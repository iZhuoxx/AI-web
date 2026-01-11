import { computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import useSetting from './setting'
import { SUPPORTED_LOCALES, type Locale } from '@/i18n'

export function useLocale() {
  const { locale } = useI18n()
  const setting = useSetting()

  const currentLocale = computed<Locale>({
    get: () => setting.value.locale,
    set: (val: Locale) => {
      setting.value.locale = val
      locale.value = val
    },
  })

  const supportedLocales = SUPPORTED_LOCALES

  const setLocale = (newLocale: Locale) => {
    currentLocale.value = newLocale
  }

  const getCurrentLocaleLabel = computed(() => {
    return supportedLocales.find((l: { value: Locale; label: string }) => l.value === currentLocale.value)?.label ?? currentLocale.value
  })

  // 同步 setting 中保存的语言到 i18n
  watch(
    () => setting.value.locale,
    (newLocale: Locale) => {
      if (newLocale && locale.value !== newLocale) {
        locale.value = newLocale
      }
    },
    { immediate: true },
  )

  return {
    currentLocale,
    supportedLocales,
    setLocale,
    getCurrentLocaleLabel,
  }
}

export default useLocale
