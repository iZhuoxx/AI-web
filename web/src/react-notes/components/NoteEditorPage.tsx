import { useState } from "react";
import { RichTextEditor } from "./RichTextEditor";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "./ui/card";
import { Button } from "./ui/button";
import { Textarea } from "./ui/textarea";
import { Input } from "./ui/input";
import { Label } from "./ui/label";
import { Badge } from "./ui/badge";
import { ScrollArea } from "./ui/scroll-area";
import { Separator } from "./ui/separator";
import { Save, Sparkles, Download, Share2, Maximize2, Minimize2 } from "lucide-react";
import { toast } from "sonner@2.0.3";

interface Note {
  id: string;
  title: string;
  content: string;
}

interface NoteEditorPageProps {
  notes: Note[];
  isGenerating: boolean;
  isFullscreen?: boolean;
  onToggleFullscreen?: () => void;
}

export function NoteEditorPage({ notes, isGenerating, isFullscreen = false, onToggleFullscreen }: NoteEditorPageProps) {
  const [noteTitle, setNoteTitle] = useState("Untitled Note");
  const [noteContent, setNoteContent] = useState(
    notes.map(n => `<h3>${n.title}</h3><p>${n.content.replace(/\n/g, '<br>')}</p>`).join('<br>')
  );
  const [suggestions, setSuggestions] = useState("");
  const [isApplyingSuggestions, setIsApplyingSuggestions] = useState(false);
  const [showAISuggestions, setShowAISuggestions] = useState(false);

  const handleApplySuggestions = () => {
    if (!suggestions.trim()) {
      toast.error("Please enter some suggestions first");
      return;
    }

    setIsApplyingSuggestions(true);
    
    // Simulate AI processing suggestions
    setTimeout(() => {
      // Mock: Add a note about the suggestions being applied
      const suggestionNote = `<p><em>✨ AI Applied: ${suggestions}</em></p>`;
      setNoteContent(noteContent + '<br>' + suggestionNote);
      setSuggestions("");
      setIsApplyingSuggestions(false);
      toast.success("AI has applied your suggestions to the note");
    }, 2000);
  };

  const handleSave = () => {
    toast.success("Note saved successfully!");
  };

  const handleExport = () => {
    // Create a blob with the note content
    const blob = new Blob([noteContent], { type: 'text/html' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${noteTitle}.html`;
    a.click();
    URL.revokeObjectURL(url);
    toast.success("Note exported successfully!");
  };

  const handleShare = () => {
    toast.info("Sharing functionality would be implemented here");
  };

  return (
    <div className="h-full flex flex-col gap-4 overflow-hidden">
      {/* Header with title and actions */}
      <div className="flex items-start justify-between gap-4 flex-wrap shrink-0">
        <div className="flex-1 min-w-[200px] space-y-2">
          <Label htmlFor="note-title">Note Title</Label>
          <Input
            id="note-title"
            value={noteTitle}
            onChange={(e) => setNoteTitle(e.target.value)}
          />
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          {isGenerating && (
            <Badge variant="default" className="gap-2">
              <Sparkles className="size-3 animate-pulse" />
              AI Generating...
            </Badge>
          )}
          <Button
            variant={showAISuggestions ? "default" : "outline"}
            size="sm"
            onClick={() => setShowAISuggestions(!showAISuggestions)}
            className="gap-2"
          >
            <Sparkles className="size-4" />
            AI Suggestions
          </Button>
          <Separator orientation="vertical" className="h-6" />
          <Button variant="outline" size="sm" onClick={handleShare}>
            <Share2 className="size-4 mr-2" />
            Share
          </Button>
          <Button variant="outline" size="sm" onClick={handleExport}>
            <Download className="size-4 mr-2" />
            Export
          </Button>
          <Button size="sm" onClick={handleSave}>
            <Save className="size-4 mr-2" />
            Save
          </Button>
          {onToggleFullscreen && (
            <>
              <Separator orientation="vertical" className="h-6" />
              <Button
                variant="outline"
                size="sm"
                onClick={onToggleFullscreen}
                className="gap-2"
              >
                {isFullscreen ? (
                  <>
                    <Minimize2 className="size-4" />
                    Exit Fullscreen
                  </>
                ) : (
                  <>
                    <Maximize2 className="size-4" />
                    Fullscreen
                  </>
                )}
              </Button>
            </>
          )}
        </div>
      </div>

      {/* Main editor area */}
      <Card className="flex-1 flex flex-col min-h-0 overflow-hidden">
        <CardHeader className="shrink-0">
          <CardTitle>Note Editor</CardTitle>
          <CardDescription>
            Edit your AI-generated notes with rich text formatting
          </CardDescription>
        </CardHeader>
        <CardContent className="flex-1 min-h-0 overflow-hidden">
          <ScrollArea className="h-full">
            <RichTextEditor
              content={noteContent}
              onChange={setNoteContent}
              placeholder="Your notes will appear here..."
            />
          </ScrollArea>
        </CardContent>
      </Card>

      {/* AI Suggestions - Toggleable */}
      {showAISuggestions && (
        <Card className="shrink-0">
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Sparkles className="size-5 text-primary" />
                <div>
                  <CardTitle className="text-base">AI Suggestions</CardTitle>
                  <CardDescription className="text-sm">
                    Tell the AI how to improve your notes
                  </CardDescription>
                </div>
              </div>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setShowAISuggestions(false)}
              >
                Hide
              </Button>
            </div>
          </CardHeader>
          <CardContent className="space-y-3">
            <Textarea
              placeholder="E.g., 'Make it more concise', 'Add more examples', 'Organize by topics'..."
              value={suggestions}
              onChange={(e) => setSuggestions(e.target.value)}
              rows={3}
              className="resize-none"
            />
            <Button
              className="w-full gap-2"
              onClick={handleApplySuggestions}
              disabled={isApplyingSuggestions || !suggestions.trim()}
            >
              <Sparkles className="size-4" />
              {isApplyingSuggestions ? "Applying..." : "Apply Suggestions"}
            </Button>
          </CardContent>
        </Card>
      )}
    </div>
  );
}