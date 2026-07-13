export type UserRole = "customer" | "adjuster" | "admin";

export type ClaimStatus =
  | "draft"
  | "submitted"
  | "processing"
  | "needs_review"
  | "approved"
  | "denied"
  | "paid"
  | "failed";

export type DocumentType = "police_report" | "damage_photo" | "id_proof" | "repair_estimate" | "other";

export interface UserOut {
  id: number;
  email: string;
  full_name: string;
  role: UserRole;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  user: UserOut;
}

export interface DocumentOut {
  id: number;
  doc_type: DocumentType;
  original_filename: string;
  mime_type: string;
  extracted_data: string | null;
  uploaded_at: string;
}

export interface ClaimOut {
  id: number;
  claim_number: string;
  status: ClaimStatus;
  incident_date: string;
  incident_description: string;
  incident_location: string;
  estimated_amount: number | null;
  approved_amount: number | null;
  ai_recommendation: string | null;
  ai_rationale: string | null;
  fraud_score: number | null;
  rules_decision: string | null;
  rules_rationale: string | null;
  review_notes: string | null;
  paid_at: string | null;
  created_at: string;
  updated_at: string;
  documents: DocumentOut[];
}

export interface NodeExecutionOut {
  node_name: string;
  output_json: string | null;
  duration_ms: number;
}

export interface WorkflowRunOut {
  id: number;
  status: "running" | "completed" | "failed";
  current_node: string | null;
  error: string | null;
  node_executions: NodeExecutionOut[];
}

export type PolicyStatus = "active" | "lapsed" | "cancelled";

export interface PolicyOut {
  id: number;
  policy_number: string;
  holder_name: string;
  vehicle_vin: string;
  vehicle_make: string;
  vehicle_model: string;
  vehicle_year: number;
  coverage_type: string;
  coverage_limit: number;
  deductible: number;
  effective_date: string;
  expiration_date: string;
  status: PolicyStatus;
}

export interface NotificationOut {
  id: number;
  claim_id: number | null;
  channel: string;
  message: string;
  created_at: string;
  read_at: string | null;
}

export interface AuditLogOut {
  id: number;
  claim_id: number | null;
  user_id: number | null;
  action: string;
  details: string | null;
  created_at: string;
}

export interface EvaluationMetrics {
  total_claims: number;
  claims_by_status: Record<string, number>;
  workflow_processed_count: number;
  ai_rules_engine_agreement_rate: number | null;
  human_reviewed_count: number;
  ai_human_agreement_rate: number | null;
  average_fraud_score: number | null;
}
