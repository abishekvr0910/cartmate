// Optional discovery shortcuts; an activity category remains the canonical type.
import type { ActivityCategory } from '../types';
// Each intent maps an emoji label, a user‑facing description, and the backend tag(s) used in LivePing.intent_tags.
// The tags are lower‑case strings that appear in the API data.

export interface IntentOption {
  id: string; // unique key used for UI state
  emoji: string; // visual emoji displayed in the pill
  labels: Record<'pl' | 'en' | 'uk' | 'ru', string>;
  tags: string[]; // backend intent tag(s) that correspond to this intent
  categories: ActivityCategory[];
}

export const INTENTS: IntentOption[] = [
  {
    id: 'walk', emoji: '🚶',
    labels: { pl: 'Spacer', en: 'Walk', uk: 'Прогулянка', ru: 'Прогулка' },
    tags: ['walk', 'spacer', 'прогул'], categories: ['walk'],
  },
  {
    id: 'study', emoji: '📚',
    labels: { pl: 'Nauka', en: 'Study', uk: 'Навчання', ru: 'Учёба' },
    tags: ['study', 'nauk', 'навчан', 'учим'], categories: ['study'],
  },
  {
    id: 'fitness', emoji: '🏃',
    labels: { pl: 'Trening', en: 'Fitness', uk: 'Тренування', ru: 'Тренировка' },
    tags: ['fitness', 'trening', 'трен'], categories: ['fitness'],
  },
  {
    id: 'social', emoji: '💬',
    labels: { pl: 'Pogadać', en: 'Talk', uk: 'Поговорити', ru: 'Поговорить' },
    tags: ['talk', 'rozmow', 'поговор'], categories: ['social'],
  },
  {
    id: 'errands', emoji: '⚡',
    labels: { pl: 'Sprawy', en: 'Errands', uk: 'Справи', ru: 'Дела' },
    tags: ['errand', 'spraw', 'справ', 'дела'], categories: ['quick'],
  },
  {
    id: 'grocery',
    emoji: '🛒',
    labels: { pl: 'Zakupy spożywcze', en: 'Groceries', uk: 'Продукти', ru: 'Продукты' },
    tags: ['grocery', 'shopping'],
    categories: ['grocery'],
  },
  {
    id: 'dinner',
    emoji: '🍕',
    labels: { pl: 'Coś zjeść', en: 'Get food', uk: 'Поїсти', ru: 'Поесть' },
    tags: ['dinner', 'food', 'meal', 'posiłek'],
    categories: ['food', 'late_night', 'cafe'],
  },
  {
    id: 'pets',
    emoji: '🐕',
    labels: { pl: 'Dla pupila', en: 'Pet supplies', uk: 'Для тварин', ru: 'Для питомца' },
    tags: ['pets', 'animals'],
    categories: [],
  },
  {
    id: 'gift',
    emoji: '🎁',
    labels: { pl: 'Prezent', en: 'Buy a gift', uk: 'Подарунок', ru: 'Подарок' },
    tags: ['gift', 'present'],
    categories: [],
  },
  {
    id: 'coffee',
    emoji: '☕',
    labels: { pl: 'Kawa', en: 'Coffee', uk: 'Кава', ru: 'Кофе' },
    tags: ['coffee', 'cafe'],
    categories: ['cafe'],
  },
  {
    id: 'healthy',
    emoji: '🥦',
    labels: { pl: 'Zdrowe zakupy', en: 'Healthy shopping', uk: 'Здорові покупки', ru: 'Здоровые покупки' },
    tags: ['healthy', 'veggies'],
    categories: ['grocery'],
  },
];
