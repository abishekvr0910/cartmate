export type TrustTier = 'Bronze' | 'Silver' | 'Gold';

export type ActivityCategory = 'study' | 'fitness' | 'walk' | 'food' | 'social' | 'grocery' | 'wholesale' | 'fashion' | 'home' | 'quick' | 'late_night' | 'cafe' | 'entertainment';

export type PingStatus = 'active' | 'matched' | 'completed' | 'cancelled' | 'expired';

export type RequestStatus = 'pending' | 'accepted' | 'declined';

export type TripStatus = 'scheduled' | 'in_progress' | 'completed' | 'cancelled' | 'emergency_sos';

export type CostSharingPolicy =
  | 'split_strictly_50_50'
  | 'buyer_pays_own'
  | 'host_treats'
  | 'companion_treats'
  | 'no_purchase_browse_only'
  | 'no_expected_spend';

export interface PlanDetailsSchema {
  what: string;
  when: string;
  meeting_point?: string | null;
  estimated_duration_minutes: number;
  cost_policy: string;
  estimated_cost_pln: number;
}

// 1. Public user profile (Discovery, Feeds, Stories - NO private contact details)
export interface UserPublic {
  id: string;
  name: string;
  avatar: string;
  bio: string;
  trust_tier: TrustTier;
  gender: string;
  city?: string;
  safe_haven_enabled: boolean;
  is_id_verified: boolean;
  campus_badge?: string | null;
  rating: number;
  manner_temperature: number;
  reviews_count: number;
  trips_completed: number;
  instagram_handle?: string | null;
  instagram_verified?: boolean;
  linkedin_handle?: string | null;
  linkedin_verified?: boolean;
  tiktok_handle?: string | null;
  tiktok_verified?: boolean;
  facebook_handle?: string | null;
  facebook_verified?: boolean;
}

// 2. Outing participant profile (phone revealed only for mutual in-person coordination)
export interface TripParticipantUser extends UserPublic {
  phone?: string | null;
}

// 3. Authenticated user's private profile (only on /api/users/me)
export interface UserPrivate extends UserPublic {
  email: string;
  phone: string;
  phone_verified_at?: string | null;
  is_selfie_verified: boolean;
  is_background_checked: boolean;
  emergency_contact?: string | null;
  emergency_contact_verified?: boolean;
  is_suspended?: boolean;
  is_banned?: boolean;
  suspension_reason?: string | null;
  assurance_marker?: string | null;
  operator_admitted_at?: string | null;
}

// Default User type represents full private user profile for the authenticated session
export type User = UserPrivate;

export interface AuthResponse {
  user: UserPrivate;
  token: string;
  message: string;
}

export interface PolishCityInfo {
  name: string;
  label: string;
  lat: number;
  lng: number;
}

export interface JoinRequest {
  id: string;
  ping_id: string;
  applicant: UserPublic;
  message: string;
  status: RequestStatus;
  created_at: string;
}

export interface LivePing {
  id: string;
  host: UserPublic;
  category: ActivityCategory;
  destination_name: string;
  destination_lat: number;
  destination_lng: number;
  address: string;
  intent_tags: string[];
  notes: string;
  women_only: boolean;
  status: PingStatus;
  distance_miles?: number;
  distance_km?: number;
  created_at: string;
  expires_at: string;
  remaining_seconds: number;
  join_requests_count: number;
}

export interface TripItemSplit {
  id: string;
  item_name: string;
  total_price_pln: number;
  payer_id: string;
  host_owes_pln: number;
  companion_owes_pln: number;
  created_at: string;
}

export interface TripSettlement {
  debtor_id: string | null;
  creditor_id: string | null;
  amount_pln: number;
}

export interface TripReviewData {
  rating: number;
  manner_badges: string[];
  feedback?: string;
}

export interface Trip {
  id: string;
  ping_id: string;
  chat_room_id?: string | null;
  plan_version: number;
  host: TripParticipantUser;
  companion: TripParticipantUser;
  destination_name: string;
  rendezvous_spot: string;
  plan_details?: PlanDetailsSchema | null;
  host_accepted: boolean;
  companion_accepted: boolean;
  host_accepted_at?: string | null;
  companion_accepted_at?: string | null;
  cancelled_by_id?: string | null;
  cancellation_reason?: string | null;
  cancelled_at?: string | null;
  status: TripStatus;
  host_checked_in: boolean;
  companion_checked_in: boolean;
  rendezvous_verified: boolean;
  pin_attempts_left?: number;
  safety_deadline_minutes: number;
  items_split: TripItemSplit[];
  total_split_pln: number;
  settlement?: TripSettlement | null;
  created_at: string;
  sos_triggered: boolean;
  sos_alert?: SosAlert | null;
  host_pin?: string | null; // Stripped from ordinary DTO; only visible to host
}

export interface SosAlert {
  id: string;
  trip_id: string;
  triggered_by_id: string;
  triggered_by_name: string;
  status: 'pending' | 'dispatched' | 'delivered' | 'fallback_required' | 'fallback_triggered' | 'failed';
  delivery_confirmed: boolean;
  dispatched_at: string;
  confirmed_at?: string | null;
  emergency_contact?: string | null;
  fallback_112_url: string;
  direct_contact_url?: string | null;
  failure_reason?: string | null;
}

export interface OtpRequestResponse {
  status: string;
  resend_cooldown_seconds: number;
  expires_in_seconds: number;
  identifier: string;
  dev_code?: string | null;
  error?: string | null;
}

export interface CityConfig {
  name: string;
  label: string;
  lat: number;
  lng: number;
  voivodeship: string;
  is_launch_hub: boolean;
}

export interface RegionConfig {
  id: string;
  name: string;
  voivodeship: string;
  center_lat: number;
  center_lng: number;
  default_radius_km: number;
  cities: CityConfig[];
}

export interface ShadowAuditStats {
  mode: string;
  total_evaluations: number;
  agreements_count: number;
  agreement_rate: number;
  average_latency_ms: number;
  recent_entries: any[];
}

export interface CommunityStats {
  completed_outings_total: number;
}

export interface HotspotSpot {
  id: string;
  name: string;
  category: ActivityCategory;
  emoji: string;
  address: string;
  target_time: string;
  description: string;
  cost_policy: string;
  votes_count: number;
  voter_avatars: string[];
  user_voted?: boolean;
  user_joined?: boolean;
  threshold: number;
  group_formed: boolean;
  outing_id?: string | null;
}

export interface ChatMessage {
  id: string;
  chat_room_id: string;
  sender_id: string;
  sender_name: string;
  sender_avatar: string;
  text: string;
  created_at: string;
  sequence: number;
}

export interface ChatRoom {
  id: string;
  scope: string;
  target_id: string;
  participant_ids: string[];
  messages: ChatMessage[];
  created_at: string;
}

export interface Outing {
  id: string;
  hotspot_id: string;
  hotspot_name: string;
  category: ActivityCategory;
  emoji: string;
  city: string;
  address: string;
  participant_ids: string[];
  participant_avatars: string[];
  chat_room_id: string;
  created_at: string;
}

export interface IntentClassificationResult {
  category: ActivityCategory;
  intent_tags: string[];
  confidence_score: number;
  suggested_duration_minutes: number;
  recommended_group_size: number;
  social_context_summary: string;
  is_safe: boolean;
}

export interface ContentSafetyResult {
  is_safe: boolean;
  safety_score: number;
  flagged_reasons: string[];
  action_recommended: 'allow' | 'warn' | 'block';
}

export interface RendezvousSuggestion {
  title: string;
  description: string;
  safety_rating: string;
  tip: string;
}

export interface WaveResponse {
  ping_id: string;
  from_user_id: string;
  from_user_name: string;
  from_user_avatar: string;
  message: string;
  timestamp: string;
}

export interface WsEventEnvelope<T = any> {
  version: number;
  id: string;
  sequence: number;
  type: string;
  occurred_at: string;
  scope: string;
  payload: T;
}

export interface ShoppingBuddySchema {
  buddy_user: UserPublicSchema;
  established_at: string;
  shared_trips_count: number;
}

export interface TripFollowUpRequest {
  would_meet_again: boolean;
  feedback?: string;
}

export interface TripFollowUpResponse {
  trip_id: string;
  user_id: string;
  would_meet_again: boolean;
  is_mutual_buddy: boolean;
  message: string;
}

// Backend contract (models.py): blocks are returned as {user: UserPublicSchema, blocked_at}.
export interface UserPublicSchema {
  id: string;
  name: string;
  avatar: string;
  bio: string;
  trust_tier: string;
  gender: string;
  city: string;
  safe_haven_enabled: boolean;
  is_id_verified: boolean;
  campus_badge?: string | null;
  rating: number;
  manner_temperature: number;
}

export interface BlockedUserSchema {
  user: UserPublicSchema;
  blocked_at: string;
}

export type ReportCategory =
  | 'harassment'
  | 'unsafe_behavior'
  | 'fake_profile'
  | 'no_show'
  | 'spam'
  | 'financial_fraud'
  | 'safety_risk'
  | 'other';

export interface ReportSchema {
  id: string;
  reporter_id: string;
  reported_user_id: string;
  trip_id?: string | null;
  outing_id?: string | null;
  evidence_chat_message_id?: string | null;
  category: ReportCategory;
  details: string;
  status: string;
  resolution_note?: string | null;
  moderator_id?: string | null;
  created_at: string;
  updated_at?: string;
}

export type ModerationAction = 'dismiss' | 'warn' | 'suspend' | 'ban';

export interface SessionInfoSchema {
  token_masked: string;
  user_id: string;
  created_at: string;
  expires_at?: string | null;
  is_revoked: boolean;
}

// --- Micro-Pods & Third Places Types ---

export interface ActivityTemplate {
  code: string;
  name: string;
  default_duration_min: number;
  structure: string;
  default_min_participants: number;
  default_max_participants: number;
  default_spend_expectation: string;
  sort_order: number;
  is_active: number;
}

export interface ThirdPlace {
  id: number;
  slug: string;
  name: string;
  kind: string;
  city: string;
  district?: string | null;
  address?: string | null;
  meeting_point: string;
  latitude: number;
  longitude: number;
  is_indoor: number;
  allowed_templates?: string[];
}

export interface PodMember {
  user_id: string;
  name: string;
  avatar: string;
  joined_at: string;
  status?: string;
}

export interface Pod {
  id: number;
  template_code: string;
  third_place_id: number;
  cohort_id?: number | null;
  created_by_user_id?: string | null;
  title?: string | null;
  language_code: string;
  exchange_language_code?: string | null;
  starts_at: string;
  ends_at: string;
  quorum_deadline_at: string;
  min_participants: number;
  max_participants: number;
  confirmed_count: number;
  spots_left: number;
  spend_expectation: 'no_expected_spend' | 'optional_spend' | 'pay_own_way';
  spend_max_minor?: number | null;
  spend_currency: string;
  status: 'forming' | 'quorum' | 'cancelled' | 'completed';
  quorum_reached_at?: string | null;
  place_name: string;
  place_address?: string | null;
  place_meeting_point: string;
  place_city: string;
  place_latitude: number;
  place_longitude: number;
  place_is_indoor: number;
  template_name: string;
  template_duration_min: number;
  members: PodMember[];
  is_member?: boolean;
}

export interface PodMessage {
  id: number;
  pod_id: number;
  sender_user_id: string;
  sender_name: string;
  sender_avatar: string;
  kind: 'user' | 'system';
  body: string;
  created_at: string;
}

export interface VoiceCallPeer {
  user_id: string;
  first_name: string;
  city: string;
}

export interface VoiceStatusResponse {
  user_id: string;
  daily_calls_used: number;
  daily_limit: number;
  cooldown_remaining_seconds: number;
  is_in_queue: boolean;
  queue_topic?: string | null;
  active_call?: {
    id: string;
    topic: string;
    status: string;
    created_at?: string | null;
    started_at?: string | null;
  } | null;
  window_open: boolean;
  window_schedule: string;
  icebreakers: string[];
  ice_servers: RTCIceServer[];
}

export interface VoiceRatingPayload {
  rating: 'respectful' | 'neutral' | 'inappropriate';
  report_tag?: string;
  details?: string;
  block_peer?: boolean;
}


