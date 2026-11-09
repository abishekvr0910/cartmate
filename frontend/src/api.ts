import type {
  AuthResponse,
  ChatMessage,
  ChatRoom,
  CommunityStats,
  ContentSafetyResult,
  HotspotSpot,
  IntentClassificationResult,
  JoinRequest,
  LivePing,
  Outing,
  RendezvousSuggestion,
  Trip,
  PlanDetailsSchema,
  User,
  WaveResponse,
  OtpRequestResponse,
  SosAlert,
  RegionConfig,
  ShadowAuditStats,
  ShoppingBuddySchema,
  TripFollowUpResponse,
  BlockedUserSchema,
  ModerationAction,
  ReportSchema,
  SessionInfoSchema,
  ActivityTemplate,
  ThirdPlace,
  Pod,
  PodMessage,
  VoiceStatusResponse,
  VoiceRatingPayload,
} from './types';

export function isNativePlatform(): boolean {
  if (typeof window !== 'undefined') {
    const cap = (window as any).Capacitor;
    if (cap && typeof cap.isNativePlatform === 'function') {
      return Boolean(cap.isNativePlatform());
    }
  }
  return false;
}

export function normalizeBackendOrigin(candidate: string | null | undefined): string | null {
  if (!candidate) return null;
  const trimmed = String(candidate).trim().replace(/\/+$/, '');
  try {
    const url = new URL(trimmed);
    if (url.protocol !== 'https:') return null;
    if (url.username || url.password) return null;
    if (url.search || url.hash) return null;
    if (url.pathname !== '' && url.pathname !== '/' && url.pathname !== '/api') return null;
    return `https://${url.host.toLowerCase()}`;
  } catch {
    return null;
  }
}

export function getApprovedNativeOrigin(): string | null {
  if (typeof window === 'undefined') return null;
  const envOrigin = (import.meta as any).env?.VITE_BACKEND_ORIGIN || (import.meta as any).env?.VITE_API_BASE_URL;
  if (envOrigin) {
    return normalizeBackendOrigin(String(envOrigin));
  }
  return null;
}

export function isApprovedBackendOrigin(candidate: string | null | undefined): boolean {
  if (!candidate) return false;
  if (!isNativePlatform()) {
    // For web browsers, only same-origin (relative /api or current window.location.origin) is approved.
    if (typeof window === 'undefined') return true;
    if (typeof URL === 'undefined') return false;
    try {
      const baseOrigin = window.location.origin || `${window.location.protocol}//${window.location.host}`;
      const url = new URL(candidate, baseOrigin);
      if (url.username || url.password) return false;
      return url.origin.toLowerCase() === baseOrigin.toLowerCase();
    } catch {
      return false;
    }
  }
  // For native platforms: strictly compare against operator/build-approved exact origin
  const approved = getApprovedNativeOrigin();
  if (!approved) return false; // Fail closed: unconfigured native app has no approved backend
  try {
    const url = new URL(candidate);
    if (url.protocol !== 'https:') return false;
    if (url.username || url.password) return false;
    const origin = `https://${url.host.toLowerCase()}`;
    return origin === approved;
  } catch {
    return false;
  }
}

export function validateApprovedBackendOrigin(candidate: string | null | undefined): string | null {
  if (!isApprovedBackendOrigin(candidate)) return null;
  return normalizeBackendOrigin(candidate);
}

function resolveImmutableBackendOrigin(): string {
  if (typeof window === 'undefined') return '';
  if (!isNativePlatform()) {
    // Web browsers strictly preserve same-origin relative routing; ignore arbitrary localStorage overrides.
    return '';
  }
  const approved = getApprovedNativeOrigin();
  if (approved) {
    return approved;
  }
  // Native platform requires an explicit, build/operator-approved HTTPS origin.
  // Missing or unapproved native configuration resolves to a designated placeholder,
  // preventing silent fallback to relative paths on the packaged client origin.
  return 'https://unconfigured-native-backend.cartmate.invalid';
}

const IMMUTABLE_BACKEND_ORIGIN = resolveImmutableBackendOrigin();

/**
 * Resolves the immutable backend base URL.
 * In a standard web browser deployment, returns '' (same origin, using relative /api and /ws).
 * In an Android Capacitor or native environment, returns the single immutable validated HTTPS origin.
 */
export function getBackendBaseUrl(): string {
  return IMMUTABLE_BACKEND_ORIGIN;
}

export function getApiBaseUrl(): string {
  const base = getBackendBaseUrl();
  return base ? `${base}/api` : '/api';
}

const BASE_URL = getApiBaseUrl();

export const POLISH_CITIES = [
  { name: 'Katowice', label: 'Katowice 🏙️ (Start)', lat: 50.2649, lng: 19.0238 },
  { name: 'Gliwice', label: 'Gliwice 🏛️ (Śląsk)', lat: 50.2945, lng: 18.6714 },
  { name: 'Sosnowiec', label: 'Sosnowiec 🛍️ (Śląsk)', lat: 50.2789, lng: 19.1306 },
  { name: 'Zabrze', label: 'Zabrze 🏭 (Śląsk)', lat: 50.3249, lng: 18.7857 },
  { name: 'Chorzów', label: 'Chorzów 🌳 (Śląsk)', lat: 50.2975, lng: 18.9546 },
  { name: 'Tychy', label: 'Tychy 🌲 (Śląsk)', lat: 50.1261, lng: 18.9868 },
  { name: 'Bytom', label: 'Bytom 🏺 (Śląsk)', lat: 50.3480, lng: 18.9328 },
  { name: 'Dąbrowa Górnicza', label: 'Dąbrowa Górnicza 🌊 (Śląsk)', lat: 50.3217, lng: 19.1947 },
];

export function getStoredUserId(): string | null {
  try {
    return localStorage.getItem('cartmate_user_id');
  } catch {
    return null;
  }
}

export function getStoredToken(): string | null {
  try {
    const token = localStorage.getItem('cartmate_token');
    if (!token) return null;
    // Session binding: ensure a session token is not reused across different native backend origins
    if (isNativePlatform()) {
      const currentBase = getBackendBaseUrl();
      const boundOrigin = localStorage.getItem('cartmate_token_bound_backend');
      if (boundOrigin && boundOrigin !== currentBase) {
        clearStoredSession();
        return null;
      }
    }
    return token;
  } catch {
    return null;
  }
}

export function setStoredSession(user: User, token?: string) {
  try {
    const resolvedToken = token || getStoredToken();
    if (resolvedToken) {
      localStorage.setItem('cartmate_user_id', user.id);
      localStorage.setItem('cartmate_token', resolvedToken);
      if (isNativePlatform()) {
        localStorage.setItem('cartmate_token_bound_backend', getBackendBaseUrl());
      }
    }
  } catch (e) {
    console.warn('localStorage not available', e);
  }
}

export function clearStoredSession() {
  try {
    localStorage.removeItem('cartmate_user_id');
    localStorage.removeItem('cartmate_token');
    localStorage.removeItem('cartmate_token_bound_backend');
  } catch (e) {
    console.warn('localStorage not available', e);
  }
}

export function getAuthHeaders(targetUrl?: string): Record<string, string> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };
  const token = getStoredToken();
  if (!token) return headers;

  const target = targetUrl || BASE_URL;
  if (!isApprovedBackendOrigin(target)) {
    // Unapproved destination or unconfigured native backend: never attach credentials!
    return headers;
  }

  headers['Authorization'] = `Bearer ${token}`;
  return headers;
}

// --- Auth APIs (Provider-Backed OTP & Sessions) ---

export async function requestOtp(identifier: string, inviteCode?: string): Promise<OtpRequestResponse> {
  const res = await fetch(`${BASE_URL}/auth/otp/request`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ identifier, invite_code: inviteCode }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Błąd wysyłania kodu OTP');
  }
  return res.json();
}

export interface EnvironmentConfig {
  environment: string;
  is_production: boolean;
  pilot_invite_required: boolean;
  operator_pilot_enabled?: boolean;
  age_assurance_required: boolean;
  age_assurance_available: boolean;
  is_explicitly_set: boolean;
  valid_environments: string[];
}

export async function fetchEnvironmentConfig(): Promise<EnvironmentConfig> {
  const res = await fetch(`${BASE_URL}/config/environment`);
  if (!res.ok) throw new Error('Could not load environment config');
  return res.json();
}

export async function fetchPilotInviteRequirement(): Promise<boolean> {
  try {
    const config = await fetchEnvironmentConfig();
    return config.pilot_invite_required === true;
  } catch {
    return true;
  }
}

export async function redeemOperatorActivation(data: {
  activation_token: string;
  name: string;
  city?: string;
  bio?: string;
  gender?: string;
}): Promise<AuthResponse> {
  const res = await fetch(`${BASE_URL}/auth/redeem-operator-activation`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Błąd aktywacji konta kodem operatora');
  }
  const authData: AuthResponse = await res.json();
  setStoredSession(authData.user, authData.token);
  return authData;
}

export async function redeemOperatorRecovery(recoveryToken: string): Promise<AuthResponse> {
  const res = await fetch(`${BASE_URL}/auth/redeem-operator-recovery`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ recovery_token: recoveryToken }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Błąd odzyskiwania konta kodem operatora');
  }
  const authData: AuthResponse = await res.json();
  setStoredSession(authData.user, authData.token);
  return authData;
}

export interface LiveAdmissionStatus {
  age_assurance_required: boolean;
  age_assurance_available: boolean;
  manual_age_check_available: boolean;
  adult_verified: boolean;
  live_access: boolean;
}

export async function fetchMyAdmission(): Promise<LiveAdmissionStatus> {
  const res = await fetch(`${BASE_URL}/users/me/admission`, { headers: getAuthHeaders() });
  if (!res.ok) throw new Error('Could not confirm live-service admission');
  return res.json();
}

export async function verifyOtp(identifier: string, code: string): Promise<AuthResponse> {
  const res = await fetch(`${BASE_URL}/auth/otp/verify`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ identifier, code }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Nieprawidłowy kod weryfikacyjny OTP');
  }
  const data: AuthResponse = await res.json();
  setStoredSession(data.user, data.token);
  return data;
}

export async function loginUser(identifier: string, code: string): Promise<AuthResponse> {
  const res = await fetch(`${BASE_URL}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ identifier, code }),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || 'Błąd logowania');
  }
  const data: AuthResponse = await res.json();
  setStoredSession(data.user, data.token);
  return data;
}

export async function registerUser(data: {
  name: string;
  phone: string;
  email: string;
  gender: string;
  city: string;
  bio?: string;
  campus_badge?: string;
  otp_code: string;
  invite_code?: string;
}): Promise<AuthResponse> {
  const res = await fetch(`${BASE_URL}/auth/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || 'Błąd rejestracji');
  }
  const result: AuthResponse = await res.json();
  setStoredSession(result.user, result.token);
  return result;
}

export async function logoutUser(): Promise<void> {
  const token = getStoredToken();
  try {
    if (token) {
      await fetch(`${BASE_URL}/auth/logout`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      });
    }
  } catch {
    // Ignore network error on logout
  } finally {
    clearStoredSession();
  }
}

// --- User Profile & Verification ---

export async function fetchCurrentUser(): Promise<User> {
  const res = await fetch(`${BASE_URL}/users/me`, {
    headers: getAuthHeaders(),
  });
  if (res.status === 401) clearStoredSession();
  if (!res.ok) throw new Error('Failed to fetch user');
  const user: User = await res.json();
  setStoredSession(user);
  return user;
}

export async function fetchAllUsers(): Promise<User[]> {
  const res = await fetch(`${BASE_URL}/users/all`, {
    headers: getAuthHeaders(),
  });
  if (!res.ok) throw new Error('Failed to fetch users');
  return res.json();
}

export async function switchUser(userId: string): Promise<User> {
  const res = await fetch(`${BASE_URL}/auth/switch-user?user_id=${userId}`, {
    method: 'POST',
    headers: getAuthHeaders(),
  });
  if (!res.ok) throw new Error('Failed to switch user');
  const data: AuthResponse = await res.json();
  setStoredSession(data.user, data.token);
  return data.user;
}

export async function getTripHostPin(tripId: string): Promise<string> {
  const res = await fetch(`${BASE_URL}/trips/${tripId}/pin`, {
    headers: getAuthHeaders(),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Błąd pobierania kodu PIN');
  }
  const data = await res.json();
  return data.pin;
}

export async function verifyId(): Promise<User> {
  const res = await fetch(`${BASE_URL}/users/verify-id`, {
    method: 'POST',
    headers: getAuthHeaders(),
  });
  if (!res.ok) throw new Error('Failed to verify ID');
  const user: User = await res.json();
  setStoredSession(user);
  return user;
}

export async function toggleSafeHaven(): Promise<User> {
  const res = await fetch(`${BASE_URL}/users/toggle-safe-haven`, {
    method: 'POST',
    headers: getAuthHeaders(),
  });
  if (!res.ok) {
    const data = await res.json();
    throw new Error(data.detail || 'Failed to toggle SafeHaven');
  }
  const user: User = await res.json();
  setStoredSession(user);
  return user;
}

export async function connectSocialAccount(provider: string, handle: string): Promise<User> {
  const res = await fetch(`${BASE_URL}/users/connect-social`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify({ provider, handle, code: 'oauth_simulated_token' }),
  });
  if (!res.ok) {
    const data = await res.json();
    throw new Error(data.detail || 'Błąd łączenia konta społecznościowego');
  }
  const user: User = await res.json();
  setStoredSession(user);
  return user;
}

export async function disconnectSocialAccount(provider: string): Promise<User> {
  const res = await fetch(`${BASE_URL}/users/disconnect-social/${provider}`, {
    method: 'POST',
    headers: getAuthHeaders(),
  });
  if (!res.ok) {
    const data = await res.json();
    throw new Error(data.detail || 'Błąd odłączania konta');
  }
  const user: User = await res.json();
  setStoredSession(user);
  return user;
}

// --- Live Pings ---

export async function fetchLivePings(params?: {
  radiusMiles?: number;
  category?: string;
  safeHavenOnly?: boolean;
  userLat?: number;
  userLng?: number;
}): Promise<LivePing[]> {
  const query = new URLSearchParams();
  const lat = params?.userLat ?? 52.2297;
  const lng = params?.userLng ?? 21.0122;
  query.append('user_lat', lat.toString());
  query.append('user_lng', lng.toString());
  if (params?.radiusMiles) query.append('radius_miles', params.radiusMiles.toString());
  if (params?.category) query.append('category', params.category);
  if (params?.safeHavenOnly) query.append('safe_haven_only', 'true');

  const res = await fetch(`${BASE_URL}/pings?${query.toString()}`, {
    headers: getAuthHeaders(),
  });
  if (!res.ok) throw new Error('Failed to fetch pings');
  return res.json();
}

export async function createLivePing(data: {
  category: string;
  destination_name: string;
  destination_lat: number;
  destination_lng: number;
  address: string;
  intent_tags: string[];
  ttl_minutes: number;
  notes?: string;
  women_only: boolean;
}): Promise<LivePing> {
  const res = await fetch(`${BASE_URL}/pings`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const errorData = await res.json();
    throw new Error(errorData.detail || 'Failed to create ping');
  }
  return res.json();
}

export async function fetchPingRequests(pingId: string): Promise<JoinRequest[]> {
  const res = await fetch(`${BASE_URL}/pings/${pingId}/requests`, {
    headers: getAuthHeaders(),
  });
  if (!res.ok) throw new Error('Failed to fetch requests');
  return res.json();
}

export async function requestToJoinPing(pingId: string, message?: string): Promise<JoinRequest> {
  const res = await fetch(`${BASE_URL}/pings/${pingId}/join`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify(message ? { message } : {}),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || 'Failed to join ping');
  }
  return res.json();
}

export async function acceptJoinRequest(pingId: string, reqId: string): Promise<Trip> {
  const res = await fetch(`${BASE_URL}/pings/${pingId}/requests/${reqId}/accept`, {
    method: 'POST',
    headers: getAuthHeaders(),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || 'Failed to accept request');
  }
  return res.json();
}

// --- Active Trips & Safety HUD ---

export async function fetchActiveTrip(): Promise<Trip | null> {
  const res = await fetch(`${BASE_URL}/trips/active/current`, {
    headers: getAuthHeaders(),
  });
  if (!res.ok) return null;
  return res.json();
}

export async function fetchTrip(tripId: string): Promise<Trip> {
  const res = await fetch(`${BASE_URL}/trips/${encodeURIComponent(tripId)}`, {
    headers: getAuthHeaders(),
  });
  if (!res.ok) throw new Error('Could not refresh outing details');
  return res.json();
}

export async function checkInTrip(tripId: string): Promise<Trip> {
  const res = await fetch(`${BASE_URL}/trips/${tripId}/checkin`, {
    method: 'POST',
    headers: getAuthHeaders(),
  });
  if (!res.ok) throw new Error('Failed to check in');
  return res.json();
}

export async function triggerTripSos(tripId: string, userConfirmed: boolean = true): Promise<Trip> {
  const res = await fetch(`${BASE_URL}/trips/${tripId}/sos`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify({ user_confirmed: userConfirmed }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Błąd uruchomienia alertu SOS');
  }
  return res.json();
}

export async function getTripSosStatus(tripId: string): Promise<SosAlert> {
  const res = await fetch(`${BASE_URL}/trips/${tripId}/sos/status`, {
    headers: getAuthHeaders(),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Błąd pobierania statusu SOS');
  }
  return res.json();
}

export async function completeTrip(tripId: string): Promise<Trip> {
  const res = await fetch(`${BASE_URL}/trips/${tripId}/complete`, {
    method: 'POST',
    headers: getAuthHeaders(),
  });
  if (!res.ok) throw new Error('Failed to complete trip');
  return res.json();
}

export async function verifyTripPin(tripId: string, pin: string): Promise<Trip> {
  const res = await fetch(`${BASE_URL}/trips/${tripId}/verify-pin`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify({ pin }),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || 'Błąd weryfikacji kodu PIN');
  }
  return res.json();
}

export async function addSplitItem(
  tripId: string,
  itemName: string,
  totalPricePln: number,
  payerId: string
): Promise<Trip> {
  const res = await fetch(`${BASE_URL}/trips/${tripId}/split-items`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify({
      item_name: itemName,
      total_price_pln: totalPricePln,
      payer_id: payerId,
      split_type: '50_50',
    }),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || 'Błąd dodawania pozycji rozliczenia');
  }
  return res.json();
}

export async function reviewTrip(
  tripId: string,
  rating: number,
  mannerBadges: string[],
  feedback?: string
): Promise<Trip> {
  const res = await fetch(`${BASE_URL}/trips/${tripId}/review`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify({
      rating,
      manner_badges: mannerBadges,
      feedback: feedback || '',
    }),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || 'Błąd zapisu oceny Manner');
  }
  return res.json();
}

export async function fetchCommunityStats(): Promise<CommunityStats> {
  const res = await fetch(`${BASE_URL}/stats`);
  if (!res.ok) throw new Error('Failed to fetch stats');
  return res.json();
}

// --- Hotspots & Group Outings (Phase 2 & 3) ---

export async function fetchHotspots(city: string = 'Katowice'): Promise<HotspotSpot[]> {
  const res = await fetch(`${BASE_URL}/hotspots?city=${encodeURIComponent(city)}`, {
    headers: getAuthHeaders(),
  });
  if (!res.ok) throw new Error('Nie udało się pobrać hotspotów');
  return res.json();
}

export async function voteHotspot(spotId: string): Promise<HotspotSpot> {
  const res = await fetch(`${BASE_URL}/hotspots/${spotId}/vote`, {
    method: 'PUT',
    headers: getAuthHeaders(),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Błąd oddawania głosu');
  }
  return res.json();
}

export async function unvoteHotspot(spotId: string): Promise<HotspotSpot> {
  const res = await fetch(`${BASE_URL}/hotspots/${spotId}/vote`, {
    method: 'DELETE',
    headers: getAuthHeaders(),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Błąd usuwania głosu');
  }
  return res.json();
}

export async function createHotspot(data: {
  city: string;
  name: string;
  category: string;
  emoji: string;
  address: string;
  target_time: string;
  description: string;
  cost_policy: string;
}): Promise<HotspotSpot> {
  const res = await fetch(`${BASE_URL}/hotspots`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Błąd tworzenia propozycji spotu');
  }
  return res.json();
}

export async function fetchOuting(outingId: string): Promise<Outing> {
  const res = await fetch(`${BASE_URL}/outings/${outingId}`, {
    headers: getAuthHeaders(),
  });
  if (!res.ok) throw new Error('Nie udało się pobrać szczegółów wyjścia');
  return res.json();
}

export async function joinOuting(outingId: string): Promise<Outing> {
  const res = await fetch(`${BASE_URL}/outings/${outingId}/join`, {
    method: 'POST',
    headers: getAuthHeaders(),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Could not join this outing');
  }
  return res.json();
}

export async function leaveOuting(outingId: string): Promise<void> {
  const res = await fetch(`${BASE_URL}/outings/${outingId}/leave`, {
    method: 'POST',
    headers: getAuthHeaders(),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Could not leave this outing');
  }
}

export async function fetchChatRoom(roomId: string): Promise<ChatRoom> {
  const res = await fetch(`${BASE_URL}/chat/rooms/${roomId}`, {
    headers: getAuthHeaders(),
  });
  if (!res.ok) throw new Error('Nie udało się pobrać czatu');
  return res.json();
}

export async function sendChatMessage(roomId: string, text: string): Promise<ChatMessage> {
  const res = await fetch(`${BASE_URL}/chat/rooms/${roomId}/messages`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify({ text }),
  });
  if (!res.ok) throw new Error('Błąd wysyłania wiadomości');
  return res.json();
}

// --- Wave & Social Interactions ---

export async function waveAtPing(pingId: string): Promise<WaveResponse> {
  const res = await fetch(`${BASE_URL}/pings/${pingId}/wave`, {
    method: 'POST',
    headers: getAuthHeaders(),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Błąd wysyłania powitania');
  }
  return res.json();
}

// --- TypeSafe AI Jev Bounded Decisions ---

export async function classifyIntent(text: string, categoryHint?: string): Promise<IntentClassificationResult> {
  const res = await fetch(`${BASE_URL}/ai/classify-intent`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify({ text, category_hint: categoryHint }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Błąd klasyfikacji intencji');
  }
  return res.json();
}

export async function screenContent(text: string): Promise<ContentSafetyResult> {
  const res = await fetch(`${BASE_URL}/ai/screen-content`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify({ text }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Błąd weryfikacji bezpieczeństwa treści');
  }
  return res.json();
}

export async function suggestRendezvous(destinationName: string, category?: string): Promise<RendezvousSuggestion[]> {
  const res = await fetch(`${BASE_URL}/ai/suggest-rendezvous`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify({ destination_name: destinationName, category: category || 'grocery' }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Błąd sugerowania punktu spotkania');
  }
  return res.json();
}

export async function getRegionsConfig(): Promise<{
  default_region: string;
  active_region: RegionConfig;
  all_regions: Record<string, RegionConfig>;
}> {
  const res = await fetch(`${BASE_URL}/config/regions`);
  if (!res.ok) throw new Error('Błąd pobierania konfiguracji regionów');
  return res.json();
}

export async function getShadowAuditStats(): Promise<ShadowAuditStats> {
  const res = await fetch(`${BASE_URL}/ai/shadow-audit`, {
    headers: getAuthHeaders(),
  });
  if (!res.ok) throw new Error('Błąd pobierania audytu AI');
  return res.json();
}

// --- Plan Acceptance, Low-Guilt Cancellation & Shopping Buddies ---

export async function updateTripPlan(tripId: string, plan: PlanDetailsSchema): Promise<Trip> {
  const res = await fetch(`${BASE_URL}/trips/${tripId}/plan`, {
    method: 'PUT',
    headers: getAuthHeaders(),
    body: JSON.stringify(plan),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to update the plan');
  }
  return res.json();
}

export async function acceptPlan(tripId: string, planVersion: number): Promise<Trip> {
  const res = await fetch(`${BASE_URL}/trips/${tripId}/accept-plan`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify({ accept: true, plan_version: planVersion }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Błąd akceptacji planu');
  }
  return res.json();
}

export async function cancelTrip(tripId: string, reason: string, note?: string): Promise<Trip> {
  const res = await fetch(`${BASE_URL}/trips/${tripId}/cancel`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify({ reason, note: note || '' }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Błąd anulowania wyjścia');
  }
  return res.json();
}

export async function submitTripFollowUp(
  tripId: string,
  wouldMeetAgain: boolean,
  vibeTags: string[],
  feedback?: string
): Promise<TripFollowUpResponse> {
  const res = await fetch(`${BASE_URL}/trips/${tripId}/follow-up`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify({
      would_meet_again: wouldMeetAgain,
      positive_tags: vibeTags,
      feedback: feedback || '',
    }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Błąd zapisu podsumowania wyjścia');
  }
  return res.json();
}

export async function fetchMyBuddies(): Promise<ShoppingBuddySchema[]> {
  const res = await fetch(`${BASE_URL}/users/me/buddies`, {
    headers: getAuthHeaders(),
  });
  if (!res.ok) throw new Error('Błąd pobierania listy zaufanych partnerów');
  return res.json();
}

// --- Safety, Abuse Reporting & User Blocking ---

export async function blockUser(userId: string, reason?: string): Promise<BlockedUserSchema> {
  const res = await fetch(`${BASE_URL}/users/${userId}/block`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify({ blocked_user_id: userId, reason: reason || '' }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Błąd blokowania użytkownika');
  }
  return res.json();
}

export async function unblockUser(userId: string): Promise<{ success: boolean; unblocked_user_id: string }> {
  const res = await fetch(`${BASE_URL}/users/${userId}/block`, {
    method: 'DELETE',
    headers: getAuthHeaders(),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Błąd odblokowania użytkownika');
  }
  return res.json();
}

export async function fetchMyBlocks(): Promise<BlockedUserSchema[]> {
  const res = await fetch(`${BASE_URL}/users/me/blocks`, {
    headers: getAuthHeaders(),
  });
  if (!res.ok) throw new Error('Błąd pobierania listy zablokowanych');
  return res.json();
}

export async function reportUser(
  reportedUserId: string,
  category: string,
  details: string,
  tripId?: string,
  evidenceChatMessageId?: string,
  outingId?: string
): Promise<ReportSchema> {
  const res = await fetch(`${BASE_URL}/reports`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify({
      reported_user_id: reportedUserId,
      category,
      details,
      trip_id: tripId || null,
      outing_id: outingId || null,
      evidence_chat_message_id: evidenceChatMessageId || null,
    }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Błąd wysyłania zgłoszenia do moderacji');
  }
  return res.json();
}

export async function fetchModerationAccess(): Promise<boolean> {
  const res = await fetch(`${BASE_URL}/moderation/access`, {
    headers: getAuthHeaders(),
  });
  if (!res.ok) return false;
  const result: { can_moderate: boolean } = await res.json();
  return result.can_moderate === true;
}

export type PilotAgeCheckMethod = 'mdowod_qr' | 'physical_identity_document';

export async function createPilotAgeCheckChallenge(): Promise<{
  account_code: string;
  challenge: string;
  expires_at: string;
}> {
  const res = await fetch(`${BASE_URL}/users/me/age-check-challenge`, {
    method: 'POST',
    headers: getAuthHeaders(),
    cache: 'no-store',
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(typeof err.detail === 'string' ? err.detail : 'Age-check code is unavailable.');
  }
  return res.json();
}

export async function attestPilotAdult(
  userId: string,
  method: PilotAgeCheckMethod,
  accountChallenge: string,
): Promise<{ adult_verified: true; expires_at: string; method: PilotAgeCheckMethod }> {
  const res = await fetch(`${BASE_URL}/moderation/users/${encodeURIComponent(userId)}/adult-attestation`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify({
      method,
      confirmed_over_18: true,
      subject_present: true,
      subject_consented: true,
      account_bound: true,
      account_challenge: accountChallenge,
    }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(typeof err.detail === 'string' ? err.detail : 'Pilot age check could not be recorded.');
  }
  return res.json();
}

export async function fetchModerationQueue(): Promise<ReportSchema[]> {
  const res = await fetch(`${BASE_URL}/moderation/queue`, {
    headers: getAuthHeaders(),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Could not load the moderation queue.');
  }
  return res.json();
}

export async function submitModerationAction(
  reportId: string,
  action: ModerationAction,
  resolutionNote: string,
): Promise<ReportSchema> {
  const res = await fetch(`${BASE_URL}/moderation/reports/${reportId}/action`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify({ action, resolution_note: resolutionNote }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Could not submit the moderation decision.');
  }
  return res.json();
}

// --- Session Security & Revocation ---

export async function fetchActiveSessions(): Promise<SessionInfoSchema[]> {
  const res = await fetch(`${BASE_URL}/auth/sessions`, {
    headers: getAuthHeaders(),
  });
  if (!res.ok) throw new Error('Błąd pobierania aktywnych sesji');
  return res.json();
}

export async function revokeAllSessions(): Promise<{ success: boolean; revoked_count: number }> {
  const res = await fetch(`${BASE_URL}/auth/revoke-all-sessions`, {
    method: 'POST',
    headers: getAuthHeaders(),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Błąd unieważniania sesji');
  }
  return res.json();
}

export async function revokeOtherSessions(): Promise<{ status: string; revoked_count: number }> {
  const res = await fetch(`${BASE_URL}/auth/revoke-other-sessions`, {
    method: 'POST',
    headers: getAuthHeaders(),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Błąd unieważniania pozostałych sesji');
  }
  return res.json();
}

// --- Micro-Pods & Third Places API ---

export async function fetchPodTemplates(): Promise<ActivityTemplate[]> {
  const res = await fetch(`${BASE_URL}/pods/templates`);
  if (!res.ok) throw new Error('Nie udało się pobrać szablonów aktywności');
  return res.json();
}

export async function fetchThirdPlaces(city?: string): Promise<ThirdPlace[]> {
  const url = city ? `${BASE_URL}/pods/places?city=${encodeURIComponent(city)}` : `${BASE_URL}/pods/places`;
  const res = await fetch(url);
  if (!res.ok) throw new Error('Nie udało się pobrać miejsc zbiórek');
  return res.json();
}

export async function fetchPodFeed(city?: string, token?: string | null): Promise<Pod[]> {
  const url = city ? `${BASE_URL}/pods/feed?city=${encodeURIComponent(city)}` : `${BASE_URL}/pods/feed`;
  const headers: Record<string, string> = {};
  if (token) headers['Authorization'] = `Bearer ${token}`;
  const res = await fetch(url, { headers });
  if (!res.ok) throw new Error('Nie udało się pobrać listy podów');
  return res.json();
}

export async function joinPod(podId: number, token: string): Promise<Pod> {
  const res = await fetch(`${BASE_URL}/pods/${podId}/join`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Nie udało się dołączyć do poda');
  }
  return res.json();
}

export async function leavePod(podId: number, token: string): Promise<Pod> {
  const res = await fetch(`${BASE_URL}/pods/${podId}/leave`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Nie udało się opuścić poda');
  }
  return res.json();
}

export async function fetchPodMessages(podId: number, token: string): Promise<PodMessage[]> {
  const res = await fetch(`${BASE_URL}/pods/${podId}/messages`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Nie udało się pobrać wiadomości poda');
  }
  return res.json();
}

export async function sendPodMessage(podId: number, text: string, token: string): Promise<PodMessage> {
  const res = await fetch(`${BASE_URL}/pods/${podId}/messages`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ text }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Nie udało się wysłać wiadomości');
  }
  return res.json();
}

export async function fetchVoiceStatus(token: string): Promise<VoiceStatusResponse> {
  const res = await fetch(`${BASE_URL}/voice/status`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Nie udało się pobrać statusu połączeń głosowych');
  }
  return res.json();
}

export async function rateVoiceCall(
  callId: string,
  payload: VoiceRatingPayload,
  token: string
): Promise<{ success: boolean; rating_id: string; call_id: string }> {
  const res = await fetch(`${BASE_URL}/voice/calls/${callId}/rate`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Nie udało się zapisać oceny rozmowy');
  }
  return res.json();
}

export async function hangupVoiceCall(
  callId: string,
  token: string,
  blockPeer = false
): Promise<{ success: boolean }> {
  const res = await fetch(`${BASE_URL}/voice/calls/${callId}/hangup`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ reason: 'user_hangup', block_peer: blockPeer }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Nie udało się zakończyć połączenia');
  }
  return res.json();
}


