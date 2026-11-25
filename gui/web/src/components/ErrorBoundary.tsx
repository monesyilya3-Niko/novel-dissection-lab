import { Component, type ReactNode } from 'react'
import Box from '@mui/material/Box'
import Typography from '@mui/material/Typography'
import Button from '@mui/material/Button'
import { useI18n } from '../state/I18nContext'

interface Props {
  children: ReactNode
  fallback?: ReactNode
}

interface State {
  hasError: boolean
  error: Error | null
}

function ErrorFallbackView({ error, onRetry }: { error: Error | null; onRetry: () => void }) {
  const { t } = useI18n()
  return (
    <Box sx={{ p: 4, textAlign: 'center' }}>
      <Typography variant="h6" color="error" gutterBottom>
        {t('error_boundary_title', '组件加载失败')}
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        {error?.message || t('error_boundary_unknown', '未知错误')}
      </Typography>
      <Button variant="outlined" onClick={onRetry} sx={{ mr: 1 }}>
        {t('error_boundary_retry', '重试')}
      </Button>
      {/* 懒加载 chunk 失败时纯重试通常会再次失败；给一个明确的整页刷新出口。 */}
      <Button variant="outlined" onClick={() => window.location.reload()}>
        {t('error_boundary_reload', '刷新页面')}
      </Button>
    </Box>
  )
}

export default class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error('ErrorBoundary caught:', error, errorInfo)
  }

  handleRetry = () => {
    this.setState({ hasError: false, error: null })
  }

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) return this.props.fallback
      return <ErrorFallbackView error={this.state.error} onRetry={this.handleRetry} />
    }
    return this.props.children
  }
}
