// 旅程进度条：HomeDashboard 内的可点击三步 Stepper。
import { useMemo, useCallback } from 'react'
import Box from '@mui/material/Box'
import Card from '@mui/material/Card'
import CardContent from '@mui/material/CardContent'
import Stepper from '@mui/material/Stepper'
import Step from '@mui/material/Step'
import StepLabel from '@mui/material/StepLabel'
import StepConnector, { stepConnectorClasses } from '@mui/material/StepConnector'
import Typography from '@mui/material/Typography'
import { styled } from '@mui/material/styles'
import CheckIcon from '@mui/icons-material/Check'
import SettingsSuggestIcon from '@mui/icons-material/SettingsSuggest'
import MenuBookIcon from '@mui/icons-material/MenuBook'
import CreateIcon from '@mui/icons-material/Create'
import type { Overview } from '../types'
import { useI18n } from '../state/I18nContext'
import { useThemeMode } from '../state/ThemeModeContext'
import { ink, stagger } from '../ink'
import type { WorkbenchKey } from '../layout/WorkbenchNav'
import { JOURNEY_DEFINITIONS, getJourneyStatuses, getJourneyActiveStep } from '../help/journeys'

const STEP_ICONS = [SettingsSuggestIcon, MenuBookIcon, CreateIcon] as const

const JourneyConnector = styled(StepConnector)(({ theme }) => ({
  [`&.${stepConnectorClasses.alternativeLabel}`]: {
    top: 18,
  },
  [`& .${stepConnectorClasses.line}`]: {
    height: 2,
    border: 0,
    backgroundColor: theme.palette.mode === 'dark' ? ink.nightLine : ink.hairline,
    borderRadius: 1,
  },
  [`&.${stepConnectorClasses.active} .${stepConnectorClasses.line}`]: {
    backgroundColor: ink.accent,
  },
  [`&.${stepConnectorClasses.completed} .${stepConnectorClasses.line}`]: {
    backgroundColor: ink.success,
  },
}))

interface JourneyStepIconProps {
  active?: boolean
  completed?: boolean
  icon?: React.ReactNode
}

function JourneyStepIcon(props: JourneyStepIconProps) {
  const { active, completed, icon } = props
  const idx = typeof icon === 'number' ? icon : 1
  const Icon = STEP_ICONS[idx - 1] ?? STEP_ICONS[0]
  const bg = completed ? ink.success : active ? ink.accent : ink.hairline
  const fg = completed || active ? '#fff' : ink.textSecondary
  return (
    <Box sx={{
      width: 36, height: 36, borderRadius: '50%',
      background: bg, color: fg,
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      border: active ? `2px solid ${ink.accent}` : 'none',
      boxShadow: (completed || active) ? '0 2px 8px rgba(16,16,20,0.12)' : 'none',
    }}>
      {completed ? <CheckIcon sx={{ fontSize: 18 }} /> : <Icon sx={{ fontSize: 18 }} />}
    </Box>
  )
}

export interface JourneyStepperProps {
  overview: Overview | null
  onNavigate: (key: WorkbenchKey) => void
}

export default function JourneyStepper({ overview, onNavigate }: JourneyStepperProps) {
  const { t, locale } = useI18n()
  const { isDark } = useThemeMode()

  const statuses = useMemo(() => getJourneyStatuses(overview), [overview])
  const activeStep = useMemo(() => getJourneyActiveStep(statuses), [statuses])

  const allDone = statuses.every((s) => s === 'done')

  const handleClick = useCallback((idx: number) => {
    const def = JOURNEY_DEFINITIONS[idx]
    if (def) onNavigate(def.workbench)
  }, [onNavigate])

  const hintKey: Record<number, string> = {
    0: 'journey_step_model_hint',
    1: 'journey_step_analyze_hint',
    2: 'journey_step_write_qc_hint',
  }

  // 进度文案：x/3 已完成
  const doneCount = statuses.filter((s) => s === 'done').length

  return (
    <Card sx={{ mb: 3, overflow: 'hidden', ...stagger(1) }} data-testid="journey-stepper">
      <Box sx={{
        height: 3,
        background: allDone ? ink.success : ink.accent,
        opacity: 0.9,
      }} />
      <CardContent sx={{ p: { xs: 2, md: 3 } }}>
        <Box sx={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', mb: 1, flexWrap: 'wrap', gap: 1 }}>
          <Typography variant="h6" sx={{ fontWeight: 600 }}>
            {t('journey_title', '使用旅程')}
          </Typography>
          <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 600 }}>
            {t('journey_progress', '{done} / {total} 已完成', { done: String(doneCount), total: '3' })}
          </Typography>
        </Box>
        <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 2.5 }}>
          {t('journey_subtitle', '点击任意一步前往对应工作台')}
        </Typography>

        <Stepper
          activeStep={activeStep}
          alternativeLabel
          connector={<JourneyConnector />}
          sx={{
            '& .MuiStepLabel-label': { mt: 1, fontWeight: 500 },
            '& .MuiStepLabel-label.Mui-active': { color: ink.accent, fontWeight: 700 },
            '& .MuiStepLabel-label.Mui-completed': { color: ink.success },
          }}
        >
          {JOURNEY_DEFINITIONS.map((def, idx) => {
            const status = statuses[idx]
            const completed = status === 'done'
            const titleText = def.title[locale] || def.title['zh-CN']
            const descText = def.description[locale] || def.description['zh-CN']
            const hint = t(hintKey[idx] as string, '')
            const showHint = hint && !completed
            return (
              <Step key={def.key} completed={completed}>
                <StepLabel
                  StepIconComponent={JourneyStepIcon}
                  onClick={() => handleClick(idx)}
                  sx={{ cursor: 'pointer', '& .MuiStepLabel-iconContainer': { cursor: 'pointer' } }}
                  data-testid={`journey-step-${def.key}`}
                >
                  <Typography variant="body2" sx={{ fontWeight: completed ? 700 : status === 'active' ? 700 : 500, color: completed ? ink.success : status === 'active' ? ink.accent : isDark ? ink.moonSoft : ink.textSecondary }}>
                    {titleText}
                  </Typography>
                  <Typography variant="caption" color="text.secondary" sx={{ display: 'block' }}>
                    {descText}
                  </Typography>
                  {showHint && (
                    <Typography variant="caption" sx={{ display: 'block', mt: 0.5, color: status === 'active' ? ink.accent : 'text.secondary', fontSize: 11 }}>
                      {hint}
                    </Typography>
                  )}
                </StepLabel>
              </Step>
            )
          })}
        </Stepper>
      </CardContent>
    </Card>
  )
}
