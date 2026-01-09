"""Routes for working with notebooks, notes, and folders."""

from __future__ import annotations 

import uuid 
from typing import Any ,Dict ,List ,Sequence 

from fastapi import APIRouter ,Depends ,HTTPException ,Response ,status 
from pydantic import ValidationError 
from sqlalchemy import Select ,select 
from sqlalchemy .orm import Session ,selectinload 
from api .dependencies import get_current_user ,require_csrf 
from api .db .database import get_db 
from api .db import models 
from api .services import openai_client 
import api .schemas as schemas 
from api .settings import settings 
from api .services .openai_utils import build_responses_payload 

router =APIRouter (prefix ="/notebooks",tags =["notebooks"])


def _notebook_query (user_id :uuid .UUID )->Select [tuple [models .Notebook ]]:
    return (
    select (models .Notebook )
    .where (models .Notebook .user_id ==user_id )
    .options (
    selectinload (models .Notebook .notes ),
    selectinload (models .Notebook .attachments ),
    selectinload (models .Notebook .folders ),
    )
    .order_by (models .Notebook .updated_at .desc ())
    )


def _note_to_schema (note :models .Note )->schemas.NoteOut :
    return schemas.NoteOut (id =note .id ,title =note .title ,content =note .content ,seq =note .seq )


def _attachment_to_schema (attachment :models .Attachment )->schemas.AttachmentOut :
    return schemas.AttachmentOut (
    id =attachment .id ,
    filename =attachment .filename ,
    mime =attachment .mime ,
    bytes =attachment .bytes ,
    sha256 =attachment .sha256 ,
    s3_object_key =attachment .s3_object_key ,
    s3_url =attachment .s3_url ,
    external_url =attachment .external_url ,
    openai_file_id =attachment .openai_file_id ,
    openai_file_purpose =attachment .openai_file_purpose ,
    enable_file_search =attachment .enable_file_search ,
    summary =attachment .summary ,
    meta =attachment .meta ,
    transcription_status =attachment .transcription_status .value ,
    transcription_lang =attachment .transcription_lang ,
    transcription_duration_sec =attachment .transcription_duration_sec ,
    created_at =attachment .created_at ,
    updated_at =attachment .updated_at ,
    )


def _folder_to_schema (folder :models .NotebookFolder )->schemas.NotebookFolderRef :
    return schemas.NotebookFolderRef (
    id =folder .id ,
    name =folder .name ,
    description =folder .description ,
    color =folder .color ,
    )


def _notebook_to_schema (notebook :models .Notebook )->schemas.NotebookOut :
    return schemas.NotebookOut (
    id =notebook .id ,
    title =notebook .title ,
    summary =notebook .summary ,
    is_archived =notebook .is_archived ,
    color =notebook .color ,
    openai_vector_store_id =notebook .openai_vector_store_id ,
    vector_store_expires_at =notebook .vector_store_expires_at ,
    notes =[_note_to_schema (n )for n in sorted (notebook .notes ,key =lambda n :n .seq )],
    attachments =[_attachment_to_schema (a )for a in notebook .attachments ],
    folders =[_folder_to_schema (folder )for folder in notebook .folders ],
    created_at =notebook .created_at ,
    updated_at =notebook .updated_at ,
    )


def _load_folders (db :Session ,user :models .User ,folder_ids :Sequence [uuid .UUID ])->List [models .NotebookFolder ]:
    if not folder_ids :
        return []

    unique_ids =list (dict .fromkeys (folder_ids ))
    folders =(
    db .execute (
    select (models .NotebookFolder ).where (
    models .NotebookFolder .user_id ==user .id ,
    models .NotebookFolder .id .in_ (unique_ids ),
    )
    )
    .scalars ()
    .all ()
    )
    found_ids ={folder .id for folder in folders }
    missing =[str (folder_id )for folder_id in unique_ids if folder_id not in found_ids ]
    if missing :
        raise HTTPException (
        status_code =status .HTTP_400_BAD_REQUEST ,
        detail =f"Notebook folder not found for ids: {', '.join(missing)}",
        )
    return folders 


def _flashcard_folder_to_schema (folder :models .FlashcardFolder )->schemas.FlashcardFolderOut :
    return schemas.FlashcardFolderOut (
    id =folder .id ,
    notebook_id =folder .notebook_id ,
    name =folder .name ,
    description =folder .description ,
    created_at =folder .created_at ,
    updated_at =folder .updated_at ,
    flashcard_ids =[card .id for card in folder .flashcards ],
    )


def _flashcard_to_schema (card :models .Flashcard )->schemas.FlashcardOut :
    return schemas.FlashcardOut (
    id =card .id ,
    notebook_id =card .notebook_id ,
    question =card .question ,
    answer =card .answer ,
    meta =card .meta ,
    folder_ids =[folder .id for folder in card .folders ],
    )


@router .get ("",response_model =List [schemas.NotebookOut ])
def list_notebooks (user :models .User =Depends (get_current_user ),db :Session =Depends (get_db ))->List [schemas.NotebookOut ]:
    """List all notebooks for the user, including notes, attachments, and folders."""
    notebooks =db .execute (_notebook_query (user .id )).scalars ().unique ().all ()
    return [_notebook_to_schema (notebook )for notebook in notebooks ]


@router .post ("",response_model =schemas.NotebookOut ,status_code =status .HTTP_201_CREATED ,dependencies =[Depends (require_csrf )])
def create_notebook (payload :schemas.NotebookCreate ,user :models .User =Depends (get_current_user ),db :Session =Depends (get_db ))->schemas.NotebookOut :
    """Create a notebook with optional nested notes and folder memberships."""
    notebook =models .Notebook (
    user_id =user .id ,
    title =payload .title ,
    summary =payload .summary ,
    is_archived =payload .is_archived or False ,
    color =payload .color ,
    openai_vector_store_id =payload .openai_vector_store_id ,
    vector_store_expires_at =payload .vector_store_expires_at ,
    )

    for note_payload in payload .notes :
        notebook .notes .append (
        models .Note (
        id =note_payload .id ,
        title =note_payload .title ,
        content =note_payload .content ,
        seq =note_payload .seq ,
        )
        )

    notebook .folders =_load_folders (db ,user ,payload .folder_ids )

    db .add (notebook )
    db .commit ()
    db .refresh (notebook )

    return _notebook_to_schema (notebook )


def _get_notebook_for_user (notebook_id :uuid .UUID ,user :models .User ,db :Session )->models .Notebook :
    notebook =(
    db .execute (_notebook_query (user .id ).where (models .Notebook .id ==notebook_id ))
    .scalars ()
    .unique ()
    .one_or_none ()
    )
    if notebook is None :
        raise HTTPException (status_code =status .HTTP_404_NOT_FOUND ,detail ="Notebook not found")
    return notebook 


@router .get ("/{notebook_id}",response_model =schemas.NotebookOut )
def get_notebook (
notebook_id :uuid .UUID ,user :models .User =Depends (get_current_user ),db :Session =Depends (get_db )
)->schemas.NotebookOut :
    """Fetch a single notebook by id, including nested relationships."""
    notebook =_get_notebook_for_user (notebook_id ,user ,db )
    return _notebook_to_schema (notebook )


@router .put ("/{notebook_id}",response_model =schemas.NotebookOut ,dependencies =[Depends (require_csrf )])
def update_notebook (
notebook_id :uuid .UUID ,payload :schemas.NotebookUpdate ,user :models .User =Depends (get_current_user ),db :Session =Depends (get_db )
)->schemas.NotebookOut :
    """Update notebook metadata, notes ordering/content, and folder membership."""
    notebook =_get_notebook_for_user (notebook_id ,user ,db )

    notebook .title =payload .title 
    notebook .summary =payload .summary 
    if payload .is_archived is not None :
        notebook .is_archived =payload .is_archived 
    notebook .color =payload .color 
    notebook .openai_vector_store_id =payload .openai_vector_store_id 
    notebook .vector_store_expires_at =payload .vector_store_expires_at 

    if payload .notes is not None :
        existing_notes ={str (note .id ):note for note in notebook .notes }
        updated_notes :list [models .Note ]=[]
        incoming_ids :set [str ]=set ()

        for idx ,note_payload in enumerate (payload .notes ):
            payload_id =str (note_payload .id )if note_payload .id is not None else None 
            if payload_id :
                incoming_ids .add (payload_id )
            if payload_id and payload_id in existing_notes :
                note =existing_notes [payload_id ]
                note .title =note_payload .title 
                note .content =note_payload .content 
            else :
                note =models .Note (
                id =note_payload .id ,
                title =note_payload .title ,
                content =note_payload .content ,
                seq =idx ,
                )
            updated_notes .append (note )

            # Two-phase reorder: push existing notes (even ones being deleted) to a temp seq before final ordering.
        temp_offset =1_000_000 
        for i ,note in enumerate (notebook .notes ):
            note .seq =temp_offset +i 
        db .flush ()

        for i ,note in enumerate (updated_notes ):
            note .seq =i 

        notebook .notes [:]=sorted (updated_notes ,key =lambda n :n .seq )

    if payload .folder_ids is not None :
        notebook .folders =_load_folders (db ,user ,payload .folder_ids )

    db .add (notebook )
    db .commit ()
    db .refresh (notebook )

    return _notebook_to_schema (notebook )


@router .delete ("/{notebook_id}",status_code =status .HTTP_204_NO_CONTENT ,dependencies =[Depends (require_csrf )])
def delete_notebook (
notebook_id :uuid .UUID ,user :models .User =Depends (get_current_user ),db :Session =Depends (get_db )
)->Response :
    """Delete a notebook and its dependent entities."""
    notebook =_get_notebook_for_user (notebook_id ,user ,db )
    db .delete (notebook )
    db .commit ()
    return Response (status_code =status .HTTP_204_NO_CONTENT )


def enforce_no_additional_properties (schema :dict ):
    """Recursively set additionalProperties=False for every object schema, and ensure required lists are present."""
    def walk (node :object ):
        if isinstance (node ,dict ):
            if node .get ("type")=="object":
                node .setdefault ("additionalProperties",False )
                props =node .get ("properties")
                if isinstance (props ,dict ):
                    node ["required"]=list (props .keys ())
                    # Recurse into common schema containers
            for key ,val in list (node .items ()):
                if isinstance (val ,(dict ,list )):
                    walk (val )
        elif isinstance (node ,list ):
            for item in node :
                walk (item )

    walk (schema )


def _extract_structured_output (payload :dict )->dict :
    """Extract the first structured/json response block from Responses API payload."""
    if not isinstance (payload ,dict ):
        return {}

        # Newer Responses API can expose parsed JSON at the top level or as the first parsed item.
    parsed =payload .get ("output_parsed")
    if isinstance (parsed ,dict ):
        return parsed 
    if isinstance (parsed ,list )and parsed :
        first =parsed [0 ]
        if isinstance (first ,dict ):
            return first 

    output =payload .get ("output")or []
    for item in output :
        if not isinstance (item ,dict ):
            continue 
            # Some SDKs place parsed JSON alongside content
        item_parsed =item .get ("parsed")
        if isinstance (item_parsed ,dict ):
            return item_parsed 
        if isinstance (item_parsed ,list ):
            for candidate in item_parsed :
                if isinstance (candidate ,dict ):
                    return candidate 

        content_list =item .get ("content")or []
        for c in content_list :
            if not isinstance (c ,dict ):
                continue 
            if "parsed"in c and c .get ("parsed")is not None :
                return c .get ("parsed")or {}
            json_val =c .get ("json")
            if isinstance (json_val ,dict ):
                return json_val 
            text_val =c .get ("text")
            if isinstance (text_val ,str )and text_val .strip ():
                try :
                    import json 

                    return json .loads (text_val )
                except Exception :
                    continue 
    return {}


@router .post (
"/{notebook_id}/flashcards/generate",
response_model =schemas.FlashcardGenerateResponse ,
status_code =status .HTTP_201_CREATED ,
dependencies =[Depends (require_csrf )],
)
async def generate_flashcards_from_openai (
notebook_id :uuid .UUID ,
payload :schemas.FlashcardGenerateRequest ,
user :models .User =Depends (get_current_user ),
db :Session =Depends (get_db ),
)->schemas.FlashcardGenerateResponse :
    """Use OpenAI Responses API + selected attachments to generate flashcards into a folder."""
    notebook =_get_notebook_for_user (notebook_id ,user ,db )

    target_folder =None 
    if payload .folder_id :
        target_folder =(
        db .execute (
        select (models .FlashcardFolder )
        .where (
        models .FlashcardFolder .id ==payload .folder_id ,
        models .FlashcardFolder .user_id ==user .id ,
        )
        .options (selectinload (models .FlashcardFolder .flashcards ))
        )
        .scalars ()
        .first ()
        )
        if target_folder is None :
            raise HTTPException (status_code =status .HTTP_404_NOT_FOUND ,detail ="Flashcard folder not found")
        if target_folder .notebook_id !=notebook .id :
            raise HTTPException (
            status_code =status .HTTP_400_BAD_REQUEST ,
            detail ="目标闪卡合集不属于当前笔记本",
            )

    attachment_map ={att .id :att for att in notebook .attachments }
    requested_ids =payload .attachment_ids or [att .id for att in notebook .attachments if att .openai_file_id ]
    selected :list [models .Attachment ]=[]

    for att_id in requested_ids :
        att =attachment_map .get (att_id )
        if not att :
            raise HTTPException (status_code =status .HTTP_400_BAD_REQUEST ,detail =f"附件不存在或不属于该笔记本: {att_id}")
        if not att .openai_file_id :
            raise HTTPException (
            status_code =status .HTTP_400_BAD_REQUEST ,
            detail =f"附件 {att.filename or att.id} 尚未同步到 OpenAI（缺少 openai_file_id）",
            )
        selected .append (att )

    if not selected :
        raise HTTPException (status_code =status .HTTP_400_BAD_REQUEST ,detail ="至少需要一个已上传到 OpenAI 的附件")

    file_blocks =[{"type":"input_file","file_id":att .openai_file_id }for att in selected if att .openai_file_id ]

    model_name =payload .model or getattr (settings ,"FLASHCARD_MODEL",None )or "gpt-4o-2024-08-06"
    desired_count =payload .count 
    focus_text =(payload .focus or "").strip ()

    system_prompt =(
    "You are a bilingual study coach that creates concise Q/A flashcards in Chinese. "
    "Use the provided files (input_file) to ground every card. "
    "Each question should be clear and the answer compact (1-3 sentences). "
    "Prefer high-yield concepts, formulas, or definitions. "
    "If a count is provided, generate exactly that many cards; otherwise choose a balanced set. "
    "Always fill the structured output schema precisely."
    )

    focus_line =f"重点/Focus: {focus_text}"if focus_text else "重点/Focus: 自动选择最重要的知识点。"
    count_line =f"生成数量: {desired_count} 张"if desired_count else "生成数量: 模型自行决定。"
    file_names =", ".join (filter (None ,[att .filename or ""for att in selected ]))or "已选资料"

    user_prompt ="\n".join (
    [
    f"Notebook: {notebook.title or '未命名笔记本'}",
    f"资料文件: {file_names}",
    count_line ,
    focus_line ,
    "输出语言: 中文。",
    ]
    )

    user_content =[{"type":"input_text","text":user_prompt },*file_blocks ]
    schema =schemas.StructuredFlashcardSet .model_json_schema ()
    enforce_no_additional_properties (schema )

    openai_payload :Dict [str ,Any ]=build_responses_payload (
    {
    "model":model_name ,
    "input":[
    {"role":"system","content":[{"type":"input_text","text":system_prompt }]},
    {"role":"user","content":user_content },
    ],
    "max_output_tokens":2048 ,
    "text":{
    "format":{
    "type":"json_schema",
    "name":"StructuredFlashcardSet",
    "strict":True ,
    "schema":schema ,
    }
    },
    }
    )

    if not model_name .lower ().startswith ("gpt-5"):
        openai_payload ["temperature"]=float (0.2 )

    try :
        data =await openai_client .responses_complete (openai_payload ,timeout =60.0 )
    except RuntimeError as exc :
        raise HTTPException (status_code =status .HTTP_502_BAD_GATEWAY ,detail =str (exc ))

    structured_payload =_extract_structured_output (data )

    if not isinstance (structured_payload ,dict ):
        structured_payload ={}

    if not structured_payload .get ("folder_name"):
        structured_payload ["folder_name"]=(
        payload .folder_name 
        or (target_folder .name if target_folder else None )
        or notebook .title 
        or "AI 闪卡"
        )

    if not structured_payload .get ("flashcards"):
        raise HTTPException (status_code =status .HTTP_502_BAD_GATEWAY ,detail ="生成闪卡失败：模型未返回任何闪卡内容，请重试")

    try :
        result :schemas.StructuredFlashcardSet =schemas.StructuredFlashcardSet .model_validate (structured_payload )
    except ValidationError as exc :
        raise HTTPException (status_code =status .HTTP_502_BAD_GATEWAY ,detail =f"解析闪卡结构化输出失败: {exc}")

    folder_name =(payload .folder_name or result .folder_name or notebook .title or "AI 闪卡").strip ()
    if len (folder_name )>255 :
        folder_name =folder_name [:255 ]

    target_folder =target_folder or models .FlashcardFolder (
    user_id =user .id ,
    notebook_id =notebook .id ,
    name =folder_name ,
    description =focus_text or None ,
    )

    new_cards :list [models .Flashcard ]=[]
    for item in result .flashcards :
        card =models .Flashcard (
        user_id =user .id ,
        notebook_id =notebook .id ,
        question =item .question .strip (),
        answer =item .answer .strip (),
        meta ={"sources":item .sources }if item .sources else None ,
        )
        new_cards .append (card )
        target_folder .flashcards .append (card )

    db .add (target_folder )
    db .commit ()
    db .refresh (target_folder )
    for card in new_cards :
        db .refresh (card )

    return schemas.FlashcardGenerateResponse (
    folder =_flashcard_folder_to_schema (target_folder ),
    flashcards =[_flashcard_to_schema (card )for card in new_cards ],
    )


def _build_mind_elixir_node (node :schemas.StructuredMindMapNode ,*,is_root :bool =False )->dict :
    children =[_build_mind_elixir_node (child )for child in node .children ]
    data ={
    "id":str (uuid .uuid4 ()),
    "topic":node .title .strip ()or "未命名节点",
    }
    if is_root :
        data ["root"]=True 
        data ["expanded"]=True 
    if node .summary :
        data ["note"]=node .summary .strip ()
    if children :
        data ["children"]=children 
    return data 


def _structured_mindmap_to_data (mindmap :schemas.StructuredMindMap ,sources :list [str ]|None =None )->dict :
    meta :dict [str ,Any ]={"title":mindmap .title }
    if sources :
        meta ["sources"]=sources 

    return {
    "nodeData":_build_mind_elixir_node (mindmap .root ,is_root =True ),
    "linkData":{},
    "template":"right",
    "direction":1 ,
    "meta":meta ,
    }


@router .post (
"/{notebook_id}/mindmaps/generate",
response_model =schemas.MindMapOut ,
status_code =status .HTTP_201_CREATED ,
dependencies =[Depends (require_csrf )],
)
async def generate_mindmap_from_openai (
notebook_id :uuid .UUID ,
payload :schemas.MindMapGenerateRequest ,
user :models .User =Depends (get_current_user ),
db :Session =Depends (get_db ),
)->schemas.MindMapOut :
    """Use OpenAI Responses API to build a structured mind map from notebook attachments."""
    notebook =_get_notebook_for_user (notebook_id ,user ,db )

    attachment_map ={att .id :att for att in notebook .attachments }
    requested_ids =payload .attachment_ids or [att .id for att in notebook .attachments if att .openai_file_id ]
    selected :list [models .Attachment ]=[]

    for att_id in requested_ids :
        att =attachment_map .get (att_id )
        if not att :
            raise HTTPException (status_code =status .HTTP_400_BAD_REQUEST ,detail =f"附件不存在或不属于该笔记本: {att_id}")
        if not att .openai_file_id :
            raise HTTPException (
            status_code =status .HTTP_400_BAD_REQUEST ,
            detail =f"附件 {att.filename or att.id} 尚未同步到 OpenAI（缺少 openai_file_id）",
            )
        selected .append (att )

    if not selected :
        raise HTTPException (status_code =status .HTTP_400_BAD_REQUEST ,detail ="至少需要一个已上传到 OpenAI 的附件")

    file_blocks =[{"type":"input_file","file_id":att .openai_file_id }for att in selected if att .openai_file_id ]

    model_name =payload .model or getattr (settings ,"MINDMAP_MODEL",None )or "gpt-4o-2024-08-06"
    focus_text =(payload .focus or "").strip ()
    user_title =(payload .title or notebook .title or "AI 思维导图").strip ()

    system_prompt =(
    "You are a bilingual study assistant that creates concise mind maps in Chinese. "
    "Use the provided files (input_file) as sources. "
    "Return a clean hierarchical structure with a single root and 3-8 main branches, depth 2-3. "
    "Keep titles short, add optional summaries when helpful, and avoid markdown. "
    "Always follow the JSON schema strictly."
    )

    focus_line =f"聚焦/Focus: {focus_text}"if focus_text else "聚焦/Focus: 课程的关键概念、关系和步骤。"
    file_names =", ".join (filter (None ,[att .filename or ""for att in selected ]))or "已选资料"

    user_prompt ="\n".join (
    [
    f"Notebook: {notebook.title or '未命名笔记本'}",
    f"Mind map title: {user_title}",
    f"资料文件: {file_names}",
    focus_line ,
    "输出语言: 中文。",
    ]
    )

    user_content =[{"type":"input_text","text":user_prompt },*file_blocks ]
    schema =schemas.StructuredMindMap .model_json_schema ()
    enforce_no_additional_properties (schema )

    openai_payload :Dict [str ,Any ]=build_responses_payload (
    {
    "model":model_name ,
    "input":[
    {"role":"system","content":[{"type":"input_text","text":system_prompt }]},
    {"role":"user","content":user_content },
    ],
    "max_output_tokens":2048 ,
    "text":{
    "format":{
    "type":"json_schema",
    "name":"StructuredMindMap",
    "strict":True ,
    "schema":schema ,
    }
    },
    }
    )

    if not model_name .lower ().startswith ("gpt-5"):
        openai_payload ["temperature"]=float (0.2 )

    try :
        data =await openai_client .responses_complete (openai_payload ,timeout =60.0 )
    except RuntimeError as exc :
        raise HTTPException (status_code =status .HTTP_502_BAD_GATEWAY ,detail =str (exc ))

    structured_payload =_extract_structured_output (data )or {}

    try :
        result :schemas.StructuredMindMap =schemas.StructuredMindMap .model_validate (structured_payload )
    except ValidationError as exc :
        raise HTTPException (status_code =status .HTTP_502_BAD_GATEWAY ,detail =f"解析思维导图结构化输出失败: {exc}")

    title =(payload .title or result .title or notebook .title or "AI 思维导图").strip ()
    if len (title )>255 :
        title =title [:255 ]
    sources =[
    att .filename or getattr (att ,"s3_object_key",None )or str (att .id )
    for att in selected 
    ]
    data_payload =_structured_mindmap_to_data (result ,sources )

    mindmap =models .MindMap (
    user_id =user .id ,
    notebook_id =notebook .id ,
    title =title ,
    data =data_payload ,
    )

    db .add (mindmap )
    db .commit ()
    db .refresh (mindmap )

    return schemas.MindMapOut .model_validate (mindmap )


@router .post (
"/title",
response_model =schemas.TitleGenerateResponse ,
dependencies =[Depends (require_csrf )],
)
async def generate_note_title (
payload :schemas.TitleGenerateRequest ,
user :models .User =Depends (get_current_user ),
)->schemas.TitleGenerateResponse :
    """Return a concise title suggestion for note content using OpenAI Responses API."""
    # Authorization is handled by dependencies; just validate payload here.
    content =payload .content .strip ()
    if not content :
        raise HTTPException (status_code =status .HTTP_400_BAD_REQUEST ,detail ="内容不能为空")

    system_prompt =(
    "你是一名笔记标题助手。请为给定内容生成一个简短且清晰的标题，"
    "总长度不超过10个字符（中英文均按单字符计数），能够准确概括核心含义。"
    "标题不要使用引号、句号或多余的标点，并保持与内容语言一致。"
    )

    # Responses API expects input_text instead of text.
    messages =[
    {"role":"system","content":[{"type":"input_text","text":system_prompt }]},
    {"role":"user","content":[{"type":"input_text","text":content }]},
    ]

    try :
        data =await openai_client .responses_complete (
        model ="gpt-4.1-nano",
        input =messages ,
        max_output_tokens =80 ,
        temperature =0.3 ,
        timeout =20.0 ,
        )
    except Exception as exc :# pragma: no cover - fallback when network errors occur
        raise HTTPException (status_code =status .HTTP_502_BAD_GATEWAY ,detail =f"请求标题生成失败：{exc}")

    def _extract_text (payload :dict )->str :
        """Try to pull the first text reply from a Responses API payload."""
        if not isinstance (payload ,dict ):
            return ""

        output =payload .get ("output")or []
        if isinstance (output ,list )and output :
            first =output [0 ]
            if isinstance (first ,dict ):
                content_list =first .get ("content")or []
                for item in content_list :
                    if isinstance (item ,dict ):
                        text_val =item .get ("text")
                        if isinstance (text_val ,str ):
                            return text_val 
        return ""

    raw_title =_extract_text (data )

    title =(raw_title or "").strip ()
    if not title :
        raise HTTPException (status_code =status .HTTP_502_BAD_GATEWAY ,detail ="生成标题失败：模型未返回结果")

        # Enforce length limit to avoid overly long titles.
    if len (title )>15 :
        title =title [:15 ]

    return schemas.TitleGenerateResponse (title =title )


def _quiz_question_to_schema (q :models .QuizQuestion )->schemas.QuizQuestionOut :
    return schemas.QuizQuestionOut (
    id =q .id ,
    notebook_id =q .notebook_id ,
    question =q .question ,
    options =q .options ,
    correct_index =q .correct_index ,
    hint =q .hint ,
    meta =q .meta ,
    is_favorite =q .is_favorite ,
    created_at =q .created_at ,
    updated_at =q .updated_at ,
    folder_ids =[folder .id for folder in q .folders ],
    )


def _quiz_folder_to_schema (folder :models .QuizFolder )->schemas.QuizFolderOut :
    return schemas.QuizFolderOut (
    id =folder .id ,
    notebook_id =folder .notebook_id ,
    name =folder .name ,
    created_at =folder .created_at ,
    updated_at =folder .updated_at ,
    question_ids =[q .id for q in folder .questions ],
    )


@router .post (
"/{notebook_id}/quizzes/generate",
response_model =schemas.QuizGenerateResponse ,
status_code =status .HTTP_201_CREATED ,
dependencies =[Depends (require_csrf )],
)
async def generate_quizzes_from_openai (
notebook_id :uuid .UUID ,
payload :schemas.QuizGenerateRequest ,
user :models .User =Depends (get_current_user ),
db :Session =Depends (get_db ),
)->schemas.QuizGenerateResponse :
    """Use OpenAI Responses API + selected attachments to generate quiz questions into a folder."""
    notebook =_get_notebook_for_user (notebook_id ,user ,db )

    attachment_map ={att .id :att for att in notebook .attachments }
    requested_ids =payload .attachment_ids or [att .id for att in notebook .attachments if att .openai_file_id ]
    selected :list [models .Attachment ]=[]

    for att_id in requested_ids :
        att =attachment_map .get (att_id )
        if not att :
            raise HTTPException (status_code =status .HTTP_400_BAD_REQUEST ,detail =f"附件不存在或不属于该笔记本: {att_id}")
        if not att .openai_file_id :
            raise HTTPException (
            status_code =status .HTTP_400_BAD_REQUEST ,
            detail =f"附件 {att.filename or att.id} 尚未同步到 OpenAI（缺少 openai_file_id）",
            )
        selected .append (att )

    if not selected :
        raise HTTPException (status_code =status .HTTP_400_BAD_REQUEST ,detail ="至少需要一个已上传到 OpenAI 的附件")

    file_blocks =[{"type":"input_file","file_id":att .openai_file_id }for att in selected if att .openai_file_id ]

    model_name =payload .model or getattr (settings ,"QUIZ_MODEL",None )or "gpt-4o-2024-08-06"
    desired_count =payload .count or 10 
    focus_text =(payload .focus or "").strip ()

    system_prompt =(
    "You are a bilingual quiz generator that creates multiple-choice questions in Chinese. "
    "Use the provided files (input_file) to ground every question. "
    "Each question should be clear and have exactly 4 options (A, B, C, D) with only one correct answer. "
    "Options should be plausible but only one should be definitively correct based on the source material. "
    "Prefer high-yield concepts, definitions, formulas, or key relationships. "
    "Generate exactly the requested number of questions. "
    "Always fill the structured output schema precisely."
    )

    focus_line =f"重点/Focus: {focus_text}"if focus_text else "重点/Focus: 自动选择最重要的知识点。"
    count_line =f"生成数量: {desired_count} 道题"
    file_names =", ".join (filter (None ,[att .filename or ""for att in selected ]))or "已选资料"

    user_prompt ="\n".join (
    [
    f"Notebook: {notebook.title or '未命名笔记本'}",
    f"资料文件: {file_names}",
    count_line ,
    focus_line ,
    "输出语言: 中文。",
    "要求: 每道题必须有4个选项，只有1个正确答案。",
    ]
    )

    user_content =[{"type":"input_text","text":user_prompt },*file_blocks ]
    schema =schemas.StructuredQuizSet .model_json_schema ()
    enforce_no_additional_properties (schema )

    openai_payload :Dict [str ,Any ]=build_responses_payload (
    {
    "model":model_name ,
    "input":[
    {"role":"system","content":[{"type":"input_text","text":system_prompt }]},
    {"role":"user","content":user_content },
    ],
    "max_output_tokens":4096 ,
    "text":{
    "format":{
    "type":"json_schema",
    "name":"StructuredQuizSet",
    "strict":True ,
    "schema":schema ,
    }
    },
    }
    )

    if not model_name .lower ().startswith ("gpt-5"):
        openai_payload ["temperature"]=float (0.3 )

    try :
        data =await openai_client .responses_complete (openai_payload ,timeout =90.0 )
    except RuntimeError as exc :
        raise HTTPException (status_code =status .HTTP_502_BAD_GATEWAY ,detail =str (exc ))

    structured_payload =_extract_structured_output (data )

    if not isinstance (structured_payload ,dict ):
        structured_payload ={}

    if not structured_payload .get ("questions"):
        raise HTTPException (status_code =status .HTTP_502_BAD_GATEWAY ,detail ="生成测验失败：模型未返回任何题目，请重试")

    try :
        result :schemas.StructuredQuizSet =schemas.StructuredQuizSet .model_validate (structured_payload )
    except ValidationError as exc :
        raise HTTPException (status_code =status .HTTP_502_BAD_GATEWAY ,detail =f"解析测验结构化输出失败: {exc}")

        # Create folder name
    folder_name =(payload .folder_name or result .folder_name or notebook .title or "AI 测验").strip ()
    if len (folder_name )>255 :
        folder_name =folder_name [:255 ]

        # Create the quiz folder
    target_folder =models .QuizFolder (
    user_id =user .id ,
    notebook_id =notebook .id ,
    name =folder_name ,
    )

    new_questions :list [models .QuizQuestion ]=[]
    for item in result .questions :
        options =[opt .text for opt in item .options ]
        correct_index =next (
        (i for i ,opt in enumerate (item .options )if opt .is_correct ),
        0 ,
        )
        question =models .QuizQuestion (
        user_id =user .id ,
        notebook_id =notebook .id ,
        question =item .question .strip (),
        options =options ,
        correct_index =correct_index ,
        hint =item .hint .strip (),
        explaination =item .explaination .strip (),
        meta ={"sources":item .sources }if item .sources else None ,
        is_favorite =False ,
        )
        new_questions .append (question )
        target_folder .questions .append (question )

    db .add (target_folder )
    db .commit ()
    db .refresh (target_folder )
    for q in new_questions :
        db .refresh (q )

    return schemas.QuizGenerateResponse (
    folder =_quiz_folder_to_schema (target_folder ),
    questions =[_quiz_question_to_schema (q )for q in new_questions ],
    )
