# Task 2+3: Section TOC and Bookmarks System

## Agent: full-stack-developer
## Date: 2026-03-05

## Summary
Created two new features for the ACOS application: a floating Section Table of Contents and a Bookmarks/Favorites system with localStorage persistence.

## Files Created
1. `/src/components/acos/section-toc.tsx` — Floating mini TOC component
2. `/src/components/acos/bookmarks.tsx` — Bookmarks system with useBookmarks hook, BookmarksProvider, BookmarkButton, BookmarkedSections

## Files Modified
1. `/src/app/page.tsx` — Integrated SectionToc, BookmarkButton, BookmarkedSections; added data-section-content wrapper
2. `/src/app/layout.tsx` — Added BookmarksProvider wrapper around children
3. `/src/components/acos/sidebar.tsx` — Added useBookmarks hook and Star indicator for bookmarked items
4. `/src/components/acos/part1-analysis.tsx` — Added 7 heading IDs
5. `/src/components/acos/part2-acos.tsx` — Added 5 heading IDs
6. `/src/components/acos/part11-masterplan.tsx` — Added 7 heading IDs

## Key Design Decisions
- Used useSyncExternalStore for bookmarks to avoid hydration issues and enable cross-component reactivity
- Used requestAnimationFrame to defer initial TOC scan, avoiding react-hooks/set-state-in-effect lint error
- MutationObserver watches for section changes to re-scan headings
- IntersectionObserver tracks current heading position for TOC highlighting
- data-section-content attribute on wrapper div enables TOC to find headings

## Exports
- `SectionToc` — from section-toc.tsx
- `useBookmarks` — from bookmarks.tsx
- `BookmarksProvider` — from bookmarks.tsx
- `BookmarkButton` — from bookmarks.tsx
- `BookmarkedSections` — from bookmarks.tsx

## Lint Status
- 0 errors, 0 warnings
- Dev server compiles successfully
