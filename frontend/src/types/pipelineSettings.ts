export type STTPipelineSettings = {
  provider: string
  model: string
  device: string
  computeType: string
  preprocessingEnabled: boolean
  chunkingEnabled: boolean
  chunkSeconds: number
  overlapSeconds: number
  minDurationSeconds: number
}

export type LLMPipelineSettings = {
  model: string
  temperature: number
  maxOutputTokens: number
}

export type SegmentingPipelineSettings = LLMPipelineSettings & {
  chunkSeconds: number
  mergeMaxOutputTokens: number
}

export type PipelineSettings = {
  stt: STTPipelineSettings
  refine: LLMPipelineSettings
  segmenting: SegmentingPipelineSettings
  reasoning: LLMPipelineSettings
}

export type ProcessingOptions = {
  defaults: PipelineSettings
  options: {
    sttProviders: string[]
    sttModels: string[]
    sttDevices: string[]
    sttComputeTypes: string[]
    llmModels: string[]
  }
}
