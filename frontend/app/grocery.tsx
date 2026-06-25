import React, { useCallback, useEffect, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  Platform,
  Pressable,
  ScrollView,
  Share,
  StyleSheet,
  View,
} from "react-native";
import { AutoText as Text } from "@/src/auto-text";
import { Ionicons } from "@expo/vector-icons";
import { SafeAreaView } from "react-native-safe-area-context";
import { Stack, useLocalSearchParams, useRouter } from "expo-router";
import * as Print from "expo-print";
import * as Sharing from "expo-sharing";

import { api, GroceryWeek } from "@/src/api";
import { colors, fonts, radius, shadow, spacing } from "@/src/theme";
import { addDaysISO, parseISO, startOfWeekISO, todayISO } from "@/src/date-utils";

const escapeHtml = (s: string) =>
  s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");

const buildPdfHtml = (g: GroceryWeek): string => {
  const startStr = parseISO(g.start).toLocaleDateString(undefined, {
    weekday: "long",
    month: "long",
    day: "numeric",
  });
  const endStr = parseISO(g.end).toLocaleDateString(undefined, {
    weekday: "long",
    month: "long",
    day: "numeric",
  });
  const rows = g.items
    .map(
      (it) => `
        <tr>
          <td class="check">&#9633;</td>
          <td class="name">${escapeHtml(it.name)}</td>
          <td class="count">${it.count > 1 ? `&times;${it.count}` : ""}</td>
        </tr>`,
    )
    .join("");
  return `<!DOCTYPE html>
<html><head><meta charset="utf-8"/>
<style>
  @page { margin: 36pt; }
  body { font-family: Georgia, 'Times New Roman', serif; color: #1C2841; }
  h1 { font-size: 28pt; margin: 0 0 4pt 0; letter-spacing: 0.5pt; }
  .sub { font-style: italic; color: #5A6478; margin: 0 0 4pt 0; font-size: 11pt; }
  .meta { color: #8A8A8A; margin: 0 0 18pt 0; font-size: 10pt; }
  hr { border: 0; border-top: 1pt solid #C9A646; margin: 8pt 0 18pt 0; width: 60pt; }
  table { width: 100%; border-collapse: collapse; font-size: 12pt; }
  td { padding: 6pt 4pt; border-bottom: 1pt solid #EFEAE0; vertical-align: middle; }
  td.check { width: 14pt; color: #C9A646; font-size: 16pt; }
  td.count { text-align: right; color: #8A8A8A; width: 40pt; font-size: 10pt; }
  td.name { font-size: 12pt; }
  .footer { text-align: center; font-style: italic; color: #C9A646; margin-top: 28pt; font-size: 10pt; }
</style></head>
<body>
  <h1>Grocery List</h1>
  <p class="sub">${escapeHtml(startStr)} &mdash; ${escapeHtml(endStr)}</p>
  <p class="meta">${g.items.length} unique items &middot; ${g.days_with_meals} day${g.days_with_meals === 1 ? "" : "s"} of meals planned</p>
  <hr/>
  <table>${rows}</table>
  <p class="footer">Ad maiorem Dei gloriam &mdash; Sanctus</p>
</body></html>`;
};

export default function GroceryScreen() {
  const router = useRouter();
  const params = useLocalSearchParams<{ start?: string }>();
  const start = typeof params.start === "string" ? params.start : startOfWeekISO(todayISO());
  const [data, setData] = useState<GroceryWeek | null>(null);
  const [loading, setLoading] = useState(true);
  const [exporting, setExporting] = useState(false);
  const [checked, setChecked] = useState<Record<string, boolean>>({});

  const load = useCallback(async () => {
    const res = await api<GroceryWeek>(`/meals/grocery?start=${start}`);
    setData(res);
  }, [start]);

  useEffect(() => {
    let c = false;
    (async () => {
      try {
        await load();
      } finally {
        if (!c) setLoading(false);
      }
    })();
    return () => {
      c = true;
    };
  }, [load]);

  const toShareText = (g: GroceryWeek) => {
    const lines = [
      `Sanctus Grocery List — ${g.start} → ${g.end}`,
      `(${g.days_with_meals} day${g.days_with_meals === 1 ? "" : "s"} of meals planned)`,
      "",
      ...g.items.map((it) => `• ${it.name}${it.count > 1 ? `  ×${it.count}` : ""}`),
      "",
      "Ad maiorem Dei gloriam.",
    ];
    return lines.join("\n");
  };

  const shareText = async () => {
    if (!data) return;
    const message = toShareText(data);
    try {
      if (Platform.OS === "web") {
        const nav = typeof navigator !== "undefined" ? (navigator as Navigator & { share?: (d: ShareData) => Promise<void>; clipboard?: { writeText: (s: string) => Promise<void> } }) : undefined;
        if (nav?.share) {
          await nav.share({ title: "Grocery List", text: message });
        } else if (nav?.clipboard) {
          await nav.clipboard.writeText(message);
          Alert.alert("Copied", "Grocery list copied to clipboard.");
        }
      } else {
        await Share.share({ message });
      }
    } catch (e) {
      console.warn("share failed", e);
    }
  };

  const exportPdf = async () => {
    if (!data || data.items.length === 0) return;
    setExporting(true);
    try {
      const html = buildPdfHtml(data);
      if (Platform.OS === "web") {
        // expo-print's printAsync opens the browser's print dialog → "Save as PDF".
        await Print.printAsync({ html });
      } else {
        const { uri } = await Print.printToFileAsync({ html, base64: false });
        const canShare = await Sharing.isAvailableAsync();
        if (canShare) {
          await Sharing.shareAsync(uri, {
            UTI: "com.adobe.pdf",
            mimeType: "application/pdf",
            dialogTitle: "Grocery List",
          });
        } else {
          Alert.alert("PDF saved", `Saved to: ${uri}`);
        }
      }
    } catch (e) {
      console.warn("pdf export failed", e);
      Alert.alert("Export failed", "Couldn't generate the PDF. Please try again.");
    } finally {
      setExporting(false);
    }
  };

  const promptShare = () => {
    if (!data || data.items.length === 0) return;
    Alert.alert(
      "Share grocery list",
      "Choose how to send your list.",
      [
        { text: "Cancel", style: "cancel" },
        { text: "PDF", onPress: exportPdf },
        { text: "Text", onPress: shareText },
      ],
      { cancelable: true },
    );
  };

  const endDate = parseISO(addDaysISO(start, 6));
  const startDate = parseISO(start);
  const label = `${startDate.toLocaleDateString(undefined, { month: "short", day: "numeric" })} – ${endDate.toLocaleDateString(undefined, { month: "short", day: "numeric" })}`;

  return (
    <SafeAreaView style={styles.safe} edges={["top", "bottom"]} testID="grocery-screen">
      <Stack.Screen options={{ headerShown: false }} />
      <View style={styles.headerRow}>
        <Pressable testID="grocery-back" onPress={() => router.back()} hitSlop={12}>
          <Ionicons name="chevron-back" size={26} color={colors.primary} />
        </Pressable>
        <Text style={styles.headerTitle}>Grocery List</Text>
        <View style={styles.headerActions}>
          <Pressable
            testID="grocery-pdf-button"
            onPress={exportPdf}
            disabled={!data || data.items.length === 0 || exporting}
            hitSlop={12}
            style={({ pressed }) => pressed && styles.pressed}
          >
            {exporting ? (
              <ActivityIndicator color={colors.gold} />
            ) : (
              <Ionicons
                name="document-text-outline"
                size={22}
                color={data && data.items.length ? colors.gold : colors.textMuted}
              />
            )}
          </Pressable>
          <Pressable
            testID="grocery-share-button"
            onPress={promptShare}
            disabled={!data || data.items.length === 0}
            hitSlop={12}
            style={({ pressed }) => pressed && styles.pressed}
          >
            <Ionicons
              name="share-outline"
              size={24}
              color={data && data.items.length ? colors.gold : colors.textMuted}
            />
          </Pressable>
        </View>
      </View>

      <Text style={styles.weekLabel}>{label}</Text>

      <ScrollView contentContainerStyle={styles.scroll}>
        {loading ? (
          <ActivityIndicator color={colors.gold} style={{ marginTop: spacing.xl }} />
        ) : !data || data.items.length === 0 ? (
          <View style={styles.empty}>
            <Ionicons name="basket-outline" size={36} color={colors.gold} />
            <Text style={styles.emptyTitle}>No ingredients yet</Text>
            <Text style={styles.emptyText}>
              Generate or add meals for this week in the Meals tab, then return here to see a unified shopping list.
            </Text>
            <Pressable
              testID="grocery-empty-back"
              onPress={() => router.back()}
              style={({ pressed }) => [styles.btn, pressed && styles.pressed]}
            >
              <Text style={styles.btnText}>Go to Meals</Text>
            </Pressable>
          </View>
        ) : (
          <>
            <View style={styles.summary} testID="grocery-summary">
              <Text style={styles.summaryNum}>{data.items.length}</Text>
              <Text style={styles.summaryLabel}>unique items · {data.days_with_meals} day(s) planned</Text>
            </View>
            {data.items.map((it) => {
              const isChecked = !!checked[it.name];
              return (
                <Pressable
                  key={it.name}
                  testID={`grocery-item-${it.name}`}
                  onPress={() => setChecked({ ...checked, [it.name]: !isChecked })}
                  style={[styles.item, isChecked && styles.itemChecked]}
                >
                  <View style={[styles.checkbox, isChecked && styles.checkboxOn]}>
                    {isChecked && <Ionicons name="checkmark" size={14} color={colors.gold} />}
                  </View>
                  <Text style={[styles.itemText, isChecked && styles.itemTextChecked]}>{it.name}</Text>
                  {it.count > 1 && (
                    <View style={styles.countBadge}>
                      <Text style={styles.countText}>×{it.count}</Text>
                    </View>
                  )}
                </Pressable>
              );
            })}
          </>
        )}
        <View style={{ height: spacing.xxl }} />
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.background },
  headerRow: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.md,
  },
  headerTitle: { fontFamily: fonts.headingBold, fontSize: 22, color: colors.textPrimary },
  headerActions: { flexDirection: "row", alignItems: "center", gap: spacing.md },
  weekLabel: {
    fontFamily: fonts.bodyItalic,
    fontStyle: "italic",
    color: colors.textSecondary,
    fontSize: 14,
    paddingHorizontal: spacing.lg,
  },
  scroll: { padding: spacing.lg, paddingTop: spacing.md },
  summary: {
    backgroundColor: colors.surface,
    borderRadius: radius.lg,
    padding: spacing.lg,
    marginBottom: spacing.md,
    borderWidth: 1,
    borderColor: colors.borderSoft,
    flexDirection: "row",
    alignItems: "baseline",
    gap: spacing.sm,
    ...shadow.card,
  },
  summaryNum: { fontFamily: fonts.headingBold, fontSize: 32, color: colors.gold },
  summaryLabel: { fontFamily: fonts.uiMedium, fontSize: 14, color: colors.textSecondary },
  item: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.md,
    padding: spacing.md,
    borderRadius: radius.md,
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.borderSoft,
    marginBottom: spacing.sm,
  },
  itemChecked: { opacity: 0.5 },
  checkbox: {
    width: 22,
    height: 22,
    borderRadius: 6,
    borderWidth: 1.5,
    borderColor: colors.border,
    alignItems: "center",
    justifyContent: "center",
  },
  checkboxOn: { backgroundColor: colors.primary, borderColor: colors.primary },
  itemText: { flex: 1, fontFamily: fonts.bodyRegular, fontSize: 16, color: colors.textPrimary },
  itemTextChecked: { textDecorationLine: "line-through", color: colors.textMuted },
  countBadge: {
    backgroundColor: colors.borderSoft,
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: radius.round,
  },
  countText: { fontFamily: fonts.uiSemi, fontSize: 12, color: colors.textSecondary },
  empty: { alignItems: "center", padding: spacing.xl, gap: spacing.sm },
  emptyTitle: { fontFamily: fonts.headingSemi, fontSize: 20, color: colors.textPrimary },
  emptyText: {
    fontFamily: fonts.bodyRegular,
    fontSize: 14,
    color: colors.textSecondary,
    textAlign: "center",
    lineHeight: 22,
  },
  btn: {
    paddingVertical: 12,
    paddingHorizontal: spacing.lg,
    borderRadius: radius.md,
    backgroundColor: colors.primary,
    marginTop: spacing.md,
  },
  btnText: { fontFamily: fonts.uiSemi, color: colors.gold, fontSize: 14 },
  pressed: { opacity: 0.7 },
});
