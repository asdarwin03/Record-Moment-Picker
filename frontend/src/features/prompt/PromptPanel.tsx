type PromptPanelProps = {
  isEnabled: boolean
  prompt: string
  onEnabledChange: (isEnabled: boolean) => void
  onPromptChange: (prompt: string) => void
}

export function PromptPanel({
  isEnabled,
  prompt,
  onEnabledChange,
  onPromptChange,
}: PromptPanelProps) {
  return (
    <div className={isEnabled ? 'prompt-area' : 'prompt-area disabled'}>
      <div className="prompt-head">
        <h2>Prompt</h2>
        <button
          className={isEnabled ? 'prompt-toggle active' : 'prompt-toggle'}
          type="button"
          onClick={() => onEnabledChange(!isEnabled)}
          aria-pressed={isEnabled}
        >
          <span>{isEnabled ? 'On' : 'Off'}</span>
        </button>
      </div>

      {isEnabled ? (
        <textarea
          value={prompt}
          onChange={(event) => onPromptChange(event.target.value)}
          aria-label="프롬프트 입력"
        />
      ) : null}
    </div>
  )
}
