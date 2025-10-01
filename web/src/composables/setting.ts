import { useStorage } from '@vueuse/core'


type Setting = {
  app_key: string,
  model: string,
  continuously: boolean,
}

const setting = useStorage<Setting>('setting', {
  app_key: '',
  model: 'gpt-4o-mini',
  continuously: true,
})

const useSetting = () => setting

export default useSetting
