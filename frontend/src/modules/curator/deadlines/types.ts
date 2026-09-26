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
  source_step_id: number | null;
}

export interface StepDeadline {
  step_id: number;
  module_id: number;
  module_title: string;
  module_position: number;
  step_position: number;
  title: string;
  type: string;
  own: OwnDeadline | null;
  effective: EffectiveDeadline | null;
}

export interface CourseDeadlineState {
  own: OwnDeadline | null;
  effective_due_at: string | null;
}

export interface DeadlineModule {
  id: number;
  number: number;
  title: string;
  steps: { number: string; deadline: StepDeadline }[];
}
