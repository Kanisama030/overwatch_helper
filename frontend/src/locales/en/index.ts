export const en = {
  app: {
    name: 'Overwatch Helper',
    tagline: 'Your tactical companion',
  },
  nav: {
    maps: 'Maps',
    heroes: 'Heroes',
  },
  steps: {
    step1: 'Step 1: Choose your battleground',
    step2: 'Step 2: Pick your hero',
    step3: 'Step 3: Strategy',
  },
  maps: {
    title: 'Map Selection',
    search: 'Quick find map...',
    allModes: 'All Modes',
    noResults: 'No maps found',
  },
  heroes: {
    title: 'Hero Guide',
    search: 'Search heroes...',
    filterAll: 'ALL',
    filterTank: 'TANK',
    filterDamage: 'DAMAGE',
    filterSupport: 'SUPPORT',
    bestPicks: 'Best Picks',
    avoidPicks: 'Avoid Picks',
    allHeroes: 'All Heroes',
    winRate: 'Win Rate',
    pickRate: 'Pick Rate',
    noData: 'No data available',
  },
  hero: {
    strategyTab: 'Strategy Overview',
    counterTab: 'Play Against Advisor',
    tldr: 'TLDR',
    perks: 'Perks',
    tacticalAnalysis: 'Tactical Analysis',
    threatsToYou: 'Threats to You',
    howToFight: 'How to Fight',
    recommendedSwaps: 'Recommended Swaps',
    changeHero: 'Change Hero',
    aiPlaceholder: 'AI analysis coming soon with Gemini Flash...',
    counterUnavailable: 'Counter data based on guide excerpts — full counter matrix not available',
    noCounterData: 'No counter information available for this hero.',
  },
  language: {
    en: 'EN',
    zhTW: 'ZH-TW',
    comingSoon: 'Traditional Chinese coming soon',
  },
} as const;

export type Messages = typeof en;
