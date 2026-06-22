import { useState, type ReactNode } from 'react'
import type {
  LLMPipelineSettings,
  PipelineSettings,
  ProcessingOptions,
  SegmentingPipelineSettings,
} from '../../types/pipelineSettings'

type AddRecordingDialogProps = {
  isSubmitting: boolean
  processingOptions: ProcessingOptions
  onCancel: () => void
  onSubmit: (file: File, settings: PipelineSettings) => void
}

type StageKey = keyof PipelineSettings

export function AddRecordingDialog({
  isSubmitting,
  processingOptions,
  onCancel,
  onSubmit,
}: AddRecordingDialogProps) {
  const [file, setFile] = useState<File | null>(null)
  const [settings, setSettings] = useState<PipelineSettings>(() =>
    structuredClone(processingOptions.defaults),
  )
  const [advancedStage, setAdvancedStage] = useState<StageKey | null>(null)

  return (
    <div className="recording-dialog-backdrop" role="presentation">
      <section
        className="recording-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="add-recording-title"
      >
        <header className="recording-dialog-head">
          <h2 id="add-recording-title">녹음 추가</h2>
          <button type="button" onClick={onCancel} aria-label="닫기">
            ×
          </button>
        </header>

        <>
            <label className="recording-file-picker">
              <span>{file?.name ?? '녹음 파일을 선택하세요'}</span>
              <strong>찾기</strong>
              <input
                type="file"
                accept="audio/*"
                onChange={(event) => setFile(event.target.files?.[0] ?? null)}
              />
            </label>

            <div className="pipeline-stage-grid">
              <StagePanel
                title="음성/텍스트 변환"
                model={settings.stt.model}
                models={processingOptions.options.sttModels}
                isAdvanced={advancedStage === 'stt'}
                onModelChange={(model) =>
                  setSettings({ ...settings, stt: { ...settings.stt, model } })
                }
                onToggleAdvanced={() =>
                  setAdvancedStage(advancedStage === 'stt' ? null : 'stt')
                }
              >
                <SelectField
                  label="Provider"
                  value={settings.stt.provider}
                  options={processingOptions.options.sttProviders}
                  onChange={(provider) =>
                    setSettings({
                      ...settings,
                      stt: { ...settings.stt, provider },
                    })
                  }
                />
                <SelectField
                  label="Device"
                  value={settings.stt.device}
                  options={processingOptions.options.sttDevices}
                  onChange={(device) =>
                    setSettings({ ...settings, stt: { ...settings.stt, device } })
                  }
                />
                <SelectField
                  label="Compute"
                  value={settings.stt.computeType}
                  options={processingOptions.options.sttComputeTypes}
                  onChange={(computeType) =>
                    setSettings({
                      ...settings,
                      stt: { ...settings.stt, computeType },
                    })
                  }
                />
                <ToggleField
                  label="오디오 전처리"
                  checked={settings.stt.preprocessingEnabled}
                  onChange={(preprocessingEnabled) =>
                    setSettings({
                      ...settings,
                      stt: { ...settings.stt, preprocessingEnabled },
                    })
                  }
                />
                <ToggleField
                  label="STT 청킹"
                  checked={settings.stt.chunkingEnabled}
                  onChange={(chunkingEnabled) =>
                    setSettings({
                      ...settings,
                      stt: { ...settings.stt, chunkingEnabled },
                    })
                  }
                />
                <NumberField
                  label="Chunk seconds"
                  value={settings.stt.chunkSeconds}
                  min={30}
                  max={3600}
                  onChange={(chunkSeconds) =>
                    setSettings({
                      ...settings,
                      stt: { ...settings.stt, chunkSeconds },
                    })
                  }
                />
                <NumberField
                  label="Overlap seconds"
                  value={settings.stt.overlapSeconds}
                  min={0}
                  max={120}
                  onChange={(overlapSeconds) =>
                    setSettings({
                      ...settings,
                      stt: { ...settings.stt, overlapSeconds },
                    })
                  }
                />
                <NumberField
                  label="청킹 기준 길이"
                  value={settings.stt.minDurationSeconds}
                  min={30}
                  max={14400}
                  onChange={(minDurationSeconds) =>
                    setSettings({
                      ...settings,
                      stt: { ...settings.stt, minDurationSeconds },
                    })
                  }
                />
              </StagePanel>

              <LLMStagePanel
                title="정제"
                stage={settings.refine}
                models={processingOptions.options.llmModels}
                isAdvanced={advancedStage === 'refine'}
                onChange={(refine) => setSettings({ ...settings, refine })}
                onToggleAdvanced={() =>
                  setAdvancedStage(advancedStage === 'refine' ? null : 'refine')
                }
              />

              <LLMStagePanel
                title="구간 분할"
                stage={settings.segmenting}
                models={processingOptions.options.llmModels}
                isAdvanced={advancedStage === 'segmenting'}
                onChange={(segmenting) =>
                  setSettings({
                    ...settings,
                    segmenting: segmenting as SegmentingPipelineSettings,
                  })
                }
                onToggleAdvanced={() =>
                  setAdvancedStage(
                    advancedStage === 'segmenting' ? null : 'segmenting',
                  )
                }
              >
                <NumberField
                  label="Chunk seconds"
                  value={settings.segmenting.chunkSeconds}
                  min={60}
                  max={3600}
                  onChange={(chunkSeconds) =>
                    setSettings({
                      ...settings,
                      segmenting: { ...settings.segmenting, chunkSeconds },
                    })
                  }
                />
                <NumberField
                  label="Merge output tokens"
                  value={settings.segmenting.mergeMaxOutputTokens}
                  min={256}
                  max={65536}
                  onChange={(mergeMaxOutputTokens) =>
                    setSettings({
                      ...settings,
                      segmenting: {
                        ...settings.segmenting,
                        mergeMaxOutputTokens,
                      },
                    })
                  }
                />
              </LLMStagePanel>

              <LLMStagePanel
                title="근거 탐색"
                stage={settings.reasoning}
                models={processingOptions.options.llmModels}
                isAdvanced={advancedStage === 'reasoning'}
                onChange={(reasoning) => setSettings({ ...settings, reasoning })}
                onToggleAdvanced={() =>
                  setAdvancedStage(
                    advancedStage === 'reasoning' ? null : 'reasoning',
                  )
                }
              />
            </div>

            <footer className="recording-dialog-actions">
              <button type="button" className="secondary" onClick={onCancel}>
                취소
              </button>
              <button
                type="button"
                className="primary"
                disabled={!file || isSubmitting}
                onClick={() => file && onSubmit(file, settings)}
              >
                {isSubmitting ? '업로드 중' : '추가'}
              </button>
            </footer>
        </>
      </section>
    </div>
  )
}

type StagePanelProps = {
  title: string
  model: string
  models: string[]
  isAdvanced: boolean
  onModelChange: (model: string) => void
  onToggleAdvanced: () => void
  children?: ReactNode
}

function StagePanel({
  title,
  model,
  models,
  isAdvanced,
  onModelChange,
  onToggleAdvanced,
  children,
}: StagePanelProps) {
  return (
    <article className="pipeline-stage">
      <h3>{title}</h3>
      <SelectField
        label="모델"
        value={model}
        options={models}
        onChange={onModelChange}
      />
      <button
        className="advanced-toggle"
        type="button"
        aria-expanded={isAdvanced}
        onClick={onToggleAdvanced}
      >
        고급
      </button>
      {isAdvanced ? <div className="advanced-fields">{children}</div> : null}
    </article>
  )
}

type LLMStagePanelProps = {
  title: string
  stage: LLMPipelineSettings | SegmentingPipelineSettings
  models: string[]
  isAdvanced: boolean
  onChange: (stage: LLMPipelineSettings | SegmentingPipelineSettings) => void
  onToggleAdvanced: () => void
  children?: ReactNode
}

function LLMStagePanel({
  title,
  stage,
  models,
  isAdvanced,
  onChange,
  onToggleAdvanced,
  children,
}: LLMStagePanelProps) {
  return (
    <StagePanel
      title={title}
      model={stage.model}
      models={models}
      isAdvanced={isAdvanced}
      onModelChange={(model) => onChange({ ...stage, model })}
      onToggleAdvanced={onToggleAdvanced}
    >
      <NumberField
        label="Temperature"
        value={stage.temperature}
        min={0}
        max={2}
        step={0.1}
        onChange={(temperature) => onChange({ ...stage, temperature })}
      />
      <NumberField
        label="Max output tokens"
        value={stage.maxOutputTokens}
        min={256}
        max={65536}
        onChange={(maxOutputTokens) => onChange({ ...stage, maxOutputTokens })}
      />
      {children}
    </StagePanel>
  )
}

function SelectField({
  label,
  value,
  options,
  onChange,
}: {
  label: string
  value: string
  options: string[]
  onChange: (value: string) => void
}) {
  return (
    <label className="pipeline-field">
      <span>{label}</span>
      <select value={value} onChange={(event) => onChange(event.target.value)}>
        {options.map((option) => (
          <option key={option} value={option}>
            {option}
          </option>
        ))}
      </select>
    </label>
  )
}

function NumberField({
  label,
  value,
  min,
  max,
  step = 1,
  onChange,
}: {
  label: string
  value: number
  min: number
  max: number
  step?: number
  onChange: (value: number) => void
}) {
  return (
    <label className="pipeline-field">
      <span>{label}</span>
      <input
        type="number"
        value={value}
        min={min}
        max={max}
        step={step}
        onChange={(event) => onChange(Number(event.target.value))}
      />
    </label>
  )
}

function ToggleField({
  label,
  checked,
  onChange,
}: {
  label: string
  checked: boolean
  onChange: (value: boolean) => void
}) {
  return (
    <label className="pipeline-toggle">
      <input
        type="checkbox"
        checked={checked}
        onChange={(event) => onChange(event.target.checked)}
      />
      <span>{label}</span>
    </label>
  )
}
