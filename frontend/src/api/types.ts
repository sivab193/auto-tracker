export type DocumentType =
  | "registration"
  | "insurance"
  | "pollution"
  | "road_tax"
  | "fitness"
  | "permit"
  | "driving_license"
  | "warranty"
  | "invoice"
  | "other";

export type FuelType = "petrol" | "diesel" | "cng" | "lpg" | "electric" | "hybrid";
export type ServiceType = "routine" | "repair" | "inspection" | "tyre" | "battery" | "other";
export type FamilyRole = "admin" | "member" | "viewer";
export type AlertStatus = "pending" | "sent" | "acknowledged" | "dismissed";

export interface User {
  id: number;
  email: string;
  name: string;
  preferred_language: string;
  is_active: boolean;
  is_superuser: boolean;
  telegram_chat_id: string | null;
}

export interface Vehicle {
  id: number;
  owner_id: number;
  family_id: number | null;
  registration_number: string;
  nickname: string | null;
  make: string | null;
  model: string | null;
  year: number | null;
  color: string | null;
  vin: string | null;
  fuel_type: FuelType | null;
  engine_number: string | null;
  odometer: number;
  notes: string | null;
  display_name: string;
}

export interface Document {
  id: number;
  vehicle_id: number;
  doc_type: DocumentType;
  title: string | null;
  original_filename: string;
  content_type: string;
  size_bytes: number;
  issue_date: string | null;
  expiry_date: string | null;
  document_number: string | null;
  issuer: string | null;
  ocr_confidence: number | null;
  version: number;
  is_current: boolean;
  supersedes_id: number | null;
  extracted_fields: Record<string, unknown> | null;
}

export interface OCRPreview {
  doc_type: DocumentType;
  ocr_text: string;
  ocr_confidence: number | null;
  fields: Record<string, string>;
}

export interface ServiceRecord {
  id: number;
  vehicle_id: number;
  service_type: ServiceType;
  service_date: string;
  odometer: number | null;
  cost: number;
  currency: string;
  vendor: string | null;
  description: string | null;
  next_service_date: string | null;
  next_service_odometer: number | null;
}

export interface FuelLog {
  id: number;
  vehicle_id: number;
  fill_date: string;
  odometer: number;
  quantity: number;
  price_per_unit: number | null;
  total_cost: number;
  currency: string;
  is_full_tank: boolean;
  station: string | null;
  distance: number | null;
  efficiency: number | null;
}

export interface Alert {
  id: number;
  vehicle_id: number | null;
  document_id: number | null;
  title: string;
  message: string;
  due_date: string | null;
  lead_days: number | null;
  channel: string;
  status: AlertStatus;
  sent_at: string | null;
  created_at: string;
}

export interface Member {
  id: number;
  user_id: number;
  role: FamilyRole;
  user_name: string | null;
  user_email: string | null;
}

export interface Family {
  id: number;
  name: string;
  owner_id: number;
  members: Member[];
}

export interface Invite {
  id: number;
  code: string;
  role: FamilyRole;
  max_uses: number;
  uses: number;
  expires_at: string | null;
  revoked: boolean;
}

export interface DashboardSummary {
  vehicles: number;
  documents: number;
  expiring_soon: number;
  pending_alerts: number;
  total_spend: number;
}

export interface MonthlyCost {
  month: string;
  fuel: number;
  service: number;
  total: number;
}

export interface VehicleAnalytics {
  vehicle_id: number;
  total_fuel_cost: number;
  total_service_cost: number;
  total_cost: number;
  fuel_events: number;
  service_events: number;
  avg_efficiency: number | null;
  best_efficiency: number | null;
  worst_efficiency: number | null;
  cost_per_distance: number | null;
  distance_tracked: number;
  monthly: MonthlyCost[];
}

export interface AuthConfig {
  single_user: boolean;
  app_name: string;
}
