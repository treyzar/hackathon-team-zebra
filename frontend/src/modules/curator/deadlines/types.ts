export interface DeadlineGroup {
  id: number;
  name: string;
  curator_id: number | null;
}

export interface OwnDeadline {
  due_at: string;
  set_by: number | null;
  updated_at: string;
}

export interface EffectiveDeadline {
  due_at: string;
  inherited: boolean;
  source_step_id: number;
}

export interface StepDeadlineResponse {
  step_id: number;
  module_id: number;
  type: string;
  own: OwnDeadline | null;
  effective: EffectiveDeadline | null;
}

export interface StepDeadline extends StepDeadlineResponse {
  module_title: string;
  title: string;
}

export interface DeadlineModule {
  id: number;
  number: number;
  title: string;
  steps: { number: string; deadline: StepDeadline }[];
}
