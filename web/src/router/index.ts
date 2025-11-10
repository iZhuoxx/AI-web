import { createRouter, createWebHistory, RouteRecordRaw } from 'vue-router'
import ChatApp from '@/pages/ChatApp.vue'
import PlaceholderPage from '@/pages/PlaceholderPage.vue'
import NotesListView from '@/pages/NotesListView.vue'
import NotesEditorView from '@/pages/NotesEditorView.vue'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    name: 'chat',
    component: ChatApp,
    meta: { title: '聊天' },
  },
  {
    path: '/notetaker',
    name: 'notes-list',
    component: NotesListView,
    meta: { title: '笔记' },
  },
  {
    path: '/notetaker/:id',
    name: 'note-editor',
    component: NotesEditorView,
    meta: { title: '编辑笔记' },
  },
  {
    path: '/about',
    name: 'about',
    component: PlaceholderPage,
    props: { title: '关于我们', description: '将会展示本网站的相关信息。' },
    meta: { title: '信息' },
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
