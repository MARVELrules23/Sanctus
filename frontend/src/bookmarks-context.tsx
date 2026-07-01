import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";

import {
  Bookmark,
  BookmarkInput,
  BookmarkKind,
  addBookmark,
  listBookmarks,
  removeBookmark,
} from "@/src/api";
import { useAuth } from "@/src/auth-context";

type BookmarksContextValue = {
  items: Bookmark[];
  loading: boolean;
  isBookmarked: (kind: BookmarkKind, refId: string) => boolean;
  toggle: (input: BookmarkInput) => Promise<void>;
  refresh: () => Promise<void>;
};

const BookmarksContext = createContext<BookmarksContextValue | undefined>(undefined);

export function BookmarksProvider({ children }: { children: React.ReactNode }) {
  const { user } = useAuth();
  const [items, setItems] = useState<Bookmark[]>([]);
  const [loading, setLoading] = useState(false);

  const refresh = useCallback(async () => {
    if (!user) {
      setItems([]);
      return;
    }
    setLoading(true);
    try {
      const res = await listBookmarks();
      setItems(res.items);
    } catch (e) {
      console.warn("bookmarks load failed", e);
    } finally {
      setLoading(false);
    }
  }, [user]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const isBookmarked = useCallback(
    (kind: BookmarkKind, refId: string) =>
      items.some((b) => b.kind === kind && b.ref_id === refId),
    [items],
  );

  const toggle = useCallback(
    async (input: BookmarkInput) => {
      const exists = items.some((b) => b.kind === input.kind && b.ref_id === input.ref_id);
      if (exists) {
        // optimistic remove
        setItems((prev) => prev.filter((b) => !(b.kind === input.kind && b.ref_id === input.ref_id)));
        try {
          await removeBookmark(input.kind, input.ref_id);
        } catch (e) {
          console.warn("remove bookmark failed", e);
          await refresh();
        }
      } else {
        try {
          const created = await addBookmark(input);
          setItems((prev) => [created, ...prev.filter((b) => b.bookmark_id !== created.bookmark_id)]);
        } catch (e) {
          console.warn("add bookmark failed", e);
          await refresh();
        }
      }
    },
    [items, refresh],
  );

  const value = useMemo(
    () => ({ items, loading, isBookmarked, toggle, refresh }),
    [items, loading, isBookmarked, toggle, refresh],
  );

  return <BookmarksContext.Provider value={value}>{children}</BookmarksContext.Provider>;
}

export function useBookmarks(): BookmarksContextValue {
  const ctx = useContext(BookmarksContext);
  if (!ctx) throw new Error("useBookmarks must be used within a BookmarksProvider");
  return ctx;
}
