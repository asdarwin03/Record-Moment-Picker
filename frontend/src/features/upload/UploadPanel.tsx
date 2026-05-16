type UploadPanelProps = {
  fileName: string
  onFileNameChange: (fileName: string) => void
}

export function UploadPanel({ fileName, onFileNameChange }: UploadPanelProps) {
  return (
    <section className="upload-panel" aria-labelledby="upload-title">
      <div>
        <p className="eyebrow">Record Moment Picker</p>
        <h1 id="upload-title">녹음에서 다시 봐야 할 순간을 고릅니다</h1>
      </div>

      <label className="file-drop">
        <input
          type="file"
          accept="audio/*"
          onChange={(event) =>
            onFileNameChange(event.target.files?.[0]?.name ?? '')
          }
        />
        <span className="file-drop-icon" aria-hidden="true">
          +
        </span>
        <span>{fileName || '오디오 파일 선택'}</span>
      </label>
    </section>
  )
}
