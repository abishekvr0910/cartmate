import type { TranslationDictionary } from '../locales';
import type { ActivityCategory } from '../types';

type LabelKey = keyof Pick<TranslationDictionary,
  | 'catStudy' | 'catFitness' | 'catWalk' | 'catFood' | 'catSocial'
  | 'catGrocery' | 'catWholesale' | 'catFashion' | 'catHome'
  | 'catQuick' | 'catLateNight' | 'catCafe' | 'catEntertainment'
>;

export const ACTIVITIES: ReadonlyArray<{ id: ActivityCategory; labelKey: LabelKey; emoji: string }> = [
  { id: 'social', labelKey: 'catSocial', emoji: '💬' },
  { id: 'walk', labelKey: 'catWalk', emoji: '🚶' },
  { id: 'study', labelKey: 'catStudy', emoji: '📚' },
  { id: 'fitness', labelKey: 'catFitness', emoji: '🏃' },
  { id: 'food', labelKey: 'catFood', emoji: '🍽️' },
  { id: 'cafe', labelKey: 'catCafe', emoji: '☕' },
  { id: 'grocery', labelKey: 'catGrocery', emoji: '🛒' },
  { id: 'quick', labelKey: 'catQuick', emoji: '⚡' },
  { id: 'late_night', labelKey: 'catLateNight', emoji: '🍔' },
  { id: 'wholesale', labelKey: 'catWholesale', emoji: '📦' },
  { id: 'fashion', labelKey: 'catFashion', emoji: '🛍️' },
  { id: 'home', labelKey: 'catHome', emoji: '🛋️' },
  { id: 'entertainment', labelKey: 'catEntertainment', emoji: '🎬' },
];

export function activityLabel(category: ActivityCategory, t: TranslationDictionary): string {
  const option = ACTIVITIES.find((item) => item.id === category);
  return option ? t[option.labelKey] : category;
}

export function activityEmoji(category: ActivityCategory): string {
  return ACTIVITIES.find((item) => item.id === category)?.emoji ?? '📍';
}
