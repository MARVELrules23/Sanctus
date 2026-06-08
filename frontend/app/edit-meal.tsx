import React, { useCallback, useEffect, useState } from "react";
import {
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { SafeAreaView } from "react-native-safe-area-context";
import { Stack, useLocalSearchParams, useRouter } from "expo-router";

import { api, DayDoc, LiturgicalDay, MealItem, MealPlan } from "@/src/api";
import LiturgicalBadge from "@/src/components/LiturgicalBadge";
import { colors, fonts, radius, shadow, spacing } from "@/src/theme";
import { formatLong, parseISO, todayISO } from "@/src/date-utils";

type SlotKey = "breakfast" | "lunch" | "dinner";

const emptyItem = (): MealItem => ({ name: "", description: "", ingredients: [], prep_minutes: 15 });

export default function EditMealScreen() {
  const router = useRouter();
  const params = useLocalSearchParams<{ date?: string }>();
  const date = typeof params.date === "string" ? params.date : todayISO();
  const [lit, setLit] = useState<LiturgicalDay | null>(null);
  const [breakfast, setBreakfast] = useState<MealItem>(emptyItem());
  const [lunch, setLunch] = useState<MealItem>(emptyItem());
  const [dinner, setDinner] = useState<MealItem>(emptyItem());
  const [reflection, setReflection] = useState("");
  const [loading, setLoading] = useState(true);
  const [suggesting, setSuggesting] = useState<SlotKey | null>(null);
  const [saving, setSaving] = useState(false);

  const setBySlot: Record<SlotKey, (m: MealItem) => void> = {
    breakfast: setBreakfast,
    lunch: setLunch,
    dinner: setDinner,
  };
  const getBySlot: Record<SlotKey, MealItem> = { breakfast, lunch, dinner };

  const load = useCallback(async () => {
    const [l, existing] = await Promise.all([
      api<LiturgicalDay>(`/liturgical/day?date=${date}`),
      api<DayDoc<MealPlan> | Record<string, never>>(`/meals?date=${date}`),
    ]);
    setLit(l);
    if ("plan" in existing) {
      const plan = (existing as DayDoc<MealPlan>).plan;
      setBreakfast(plan.breakfast || emptyItem());
      setLunch(plan.lunch || emptyItem());
      setDinner(plan.dinner || emptyItem());
      setReflection(plan.reflection || "");
    }
  }, [date]);

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

  const suggest = async (slot: SlotKey) => {
    setSuggesting(slot);
    try {
      const cur = getBySlot[slot];
      const item = await api<MealItem>("/meals/suggest", {
        method: "POST",
        body: { date, slot, hint: cur.name || null },
      });
      setBySlot[slot]({
        name: item.name || "",
        description: item.description || "",
        ingredients: item.ingredients || [],
        prep_minutes: item.prep_minutes || 15,
      });
    } catch (e) {
      console.warn("suggest failed", e);
    } finally {
      setSuggesting(null);
    }
  };

  const save = async () => {
    setSaving(true);
    try {
      await api<DayDoc<MealPlan>>("/meals/save", {
        method: "POST",
        body: { date, breakfast, lunch, dinner, reflection },
      });
      router.back();
    } catch (e) {
      console.warn("save failed", e);
    } finally {
      setSaving(false);
    }
  };

  return (
    <SafeAreaView style={styles.safe} edges={["top", "bottom"]} testID="edit-meal-screen">
      <Stack.Screen options={{ headerShown: false }} />
      <View style={styles.headerRow}>
        <Pressable testID="edit-meal-close" onPress={() => router.back()} hitSlop={12}>
          <Ionicons name="close" size={26} color={colors.primary} />
        </Pressable>
        <Text style={styles.headerTitle}>Plan Meals</Text>
        <Pressable
          testID="edit-meal-save"
          onPress={save}
          disabled={saving || loading}
          style={({ pressed }) => pressed && styles.pressed}
        >
          {saving ? (
            <ActivityIndicator color={colors.gold} />
          ) : (
            <Text style={styles.saveText}>Save</Text>
          )}
        </Pressable>
      </View>

      <KeyboardAvoidingView
        style={{ flex: 1 }}
        behavior={Platform.OS === "ios" ? "padding" : undefined}
        keyboardVerticalOffset={20}
      >
        <ScrollView contentContainerStyle={styles.scroll} keyboardShouldPersistTaps="handled">
          <Text style={styles.date}>{formatLong(parseISO(date))}</Text>
          {lit && (
            <View style={styles.badgeRow}>
              <LiturgicalBadge color={lit.color} label={lit.season} />
              {lit.is_abstinence && <LiturgicalBadge color="red" label="Abstinence" />}
              {lit.is_fast && <LiturgicalBadge color="purple" label="Fast" />}
            </View>
          )}

          {loading ? (
            <ActivityIndicator color={colors.gold} style={{ marginTop: spacing.xl }} />
          ) : (
            <>
              {(["breakfast", "lunch", "dinner"] as const).map((slot) => (
                <SlotEditor
                  key={slot}
                  slot={slot}
                  item={getBySlot[slot]}
                  onChange={setBySlot[slot]}
                  suggesting={suggesting === slot}
                  onSuggest={() => suggest(slot)}
                />
              ))}

              <Text style={styles.fieldLabel}>Reflection (optional)</Text>
              <TextInput
                testID="edit-meal-reflection"
                style={[styles.input, styles.multi]}
                multiline
                placeholder="Tie today's meals to the season or feast…"
                placeholderTextColor={colors.textMuted}
                value={reflection}
                onChangeText={setReflection}
              />
            </>
          )}
          <View style={{ height: spacing.xl }} />
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

function SlotEditor({
  slot,
  item,
  onChange,
  suggesting,
  onSuggest,
}: {
  slot: SlotKey;
  item: MealItem;
  onChange: (m: MealItem) => void;
  suggesting: boolean;
  onSuggest: () => void;
}) {
  const [ingDraft, setIngDraft] = useState("");
  return (
    <View style={styles.slotCard} testID={`slot-${slot}`}>
      <View style={styles.slotHeader}>
        <Text style={styles.slotLabel}>{slot.toUpperCase()}</Text>
        <Pressable
          testID={`suggest-${slot}`}
          onPress={onSuggest}
          disabled={suggesting}
          style={({ pressed }) => [styles.suggestBtn, pressed && styles.pressed]}
        >
          {suggesting ? (
            <ActivityIndicator color={colors.gold} size="small" />
          ) : (
            <>
              <Ionicons name="sparkles-outline" size={14} color={colors.gold} />
              <Text style={styles.suggestBtnText}>AI suggest</Text>
            </>
          )}
        </Pressable>
      </View>

      <TextInput
        testID={`${slot}-name`}
        style={styles.input}
        placeholder="Dish name"
        placeholderTextColor={colors.textMuted}
        value={item.name}
        onChangeText={(t) => onChange({ ...item, name: t })}
      />
      <TextInput
        testID={`${slot}-description`}
        style={[styles.input, styles.multi]}
        placeholder="Short description"
        placeholderTextColor={colors.textMuted}
        value={item.description}
        onChangeText={(t) => onChange({ ...item, description: t })}
        multiline
      />
      <View style={styles.row}>
        <Text style={styles.smallLabel}>Prep min</Text>
        <TextInput
          testID={`${slot}-prep`}
          style={[styles.input, styles.prepInput]}
          keyboardType="number-pad"
          placeholder="15"
          placeholderTextColor={colors.textMuted}
          value={String(item.prep_minutes || "")}
          onChangeText={(t) => onChange({ ...item, prep_minutes: parseInt(t || "0", 10) || 0 })}
        />
      </View>
      <Text style={styles.smallLabel}>Ingredients</Text>
      <View style={styles.ingredientList}>
        {item.ingredients.map((ing, idx) => (
          <Pressable
            key={`${ing}-${idx}`}
            onPress={() => onChange({ ...item, ingredients: item.ingredients.filter((_, i) => i !== idx) })}
            testID={`${slot}-ing-${idx}`}
            style={styles.ingPill}
          >
            <Text style={styles.ingPillText}>{ing}</Text>
            <Ionicons name="close" size={12} color={colors.textSecondary} />
          </Pressable>
        ))}
      </View>
      <View style={styles.ingRow}>
        <TextInput
          testID={`${slot}-ing-input`}
          style={[styles.input, { flex: 1 }]}
          placeholder="Add ingredient"
          placeholderTextColor={colors.textMuted}
          value={ingDraft}
          onChangeText={setIngDraft}
          onSubmitEditing={() => {
            const v = ingDraft.trim();
            if (v) {
              onChange({ ...item, ingredients: [...item.ingredients, v] });
              setIngDraft("");
            }
          }}
          returnKeyType="done"
        />
        <Pressable
          testID={`${slot}-ing-add`}
          onPress={() => {
            const v = ingDraft.trim();
            if (v) {
              onChange({ ...item, ingredients: [...item.ingredients, v] });
              setIngDraft("");
            }
          }}
          style={({ pressed }) => [styles.addBtn, pressed && styles.pressed]}
        >
          <Ionicons name="add" size={20} color={colors.gold} />
        </Pressable>
      </View>
    </View>
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
    borderBottomWidth: 1,
    borderBottomColor: colors.borderSoft,
  },
  headerTitle: { fontFamily: fonts.headingBold, fontSize: 22, color: colors.textPrimary },
  saveText: { fontFamily: fonts.uiSemi, fontSize: 16, color: colors.gold },
  scroll: { padding: spacing.lg },
  date: { fontFamily: fonts.headingBold, fontSize: 26, color: colors.textPrimary },
  badgeRow: { flexDirection: "row", flexWrap: "wrap", gap: spacing.sm, marginTop: spacing.sm, marginBottom: spacing.md },
  slotCard: {
    backgroundColor: colors.surface,
    borderRadius: radius.lg,
    padding: spacing.lg,
    borderWidth: 1,
    borderColor: colors.borderSoft,
    marginTop: spacing.md,
    ...shadow.card,
  },
  slotHeader: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", marginBottom: spacing.sm },
  slotLabel: { fontFamily: fonts.uiSemi, fontSize: 12, letterSpacing: 1.5, color: colors.gold },
  suggestBtn: {
    flexDirection: "row",
    alignItems: "center",
    gap: 4,
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: radius.round,
    backgroundColor: colors.primary,
  },
  suggestBtnText: { fontFamily: fonts.uiSemi, fontSize: 12, color: colors.gold },
  input: {
    backgroundColor: "#FAF9F6",
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: colors.border,
    paddingHorizontal: spacing.md,
    paddingVertical: 12,
    fontFamily: fonts.bodyRegular,
    fontSize: 15,
    color: colors.textPrimary,
    marginTop: spacing.sm,
  },
  multi: { minHeight: 64, textAlignVertical: "top" },
  row: { flexDirection: "row", alignItems: "center", gap: spacing.sm, marginTop: spacing.sm },
  smallLabel: { fontFamily: fonts.uiSemi, fontSize: 12, color: colors.textMuted, letterSpacing: 0.8, marginTop: spacing.sm },
  prepInput: { width: 80, marginTop: 0 },
  fieldLabel: { fontFamily: fonts.uiSemi, fontSize: 12, color: colors.textMuted, letterSpacing: 0.8, marginTop: spacing.lg },
  ingredientList: { flexDirection: "row", flexWrap: "wrap", gap: spacing.xs, marginTop: spacing.xs },
  ingPill: {
    flexDirection: "row",
    alignItems: "center",
    gap: 4,
    backgroundColor: colors.borderSoft,
    paddingHorizontal: 10,
    paddingVertical: 5,
    borderRadius: radius.round,
  },
  ingPillText: { fontFamily: fonts.bodyRegular, fontSize: 13, color: colors.textPrimary },
  ingRow: { flexDirection: "row", alignItems: "center", gap: spacing.sm, marginTop: spacing.xs },
  addBtn: {
    width: 40,
    height: 40,
    borderRadius: radius.md,
    backgroundColor: colors.primary,
    alignItems: "center",
    justifyContent: "center",
    marginTop: spacing.sm,
  },
  pressed: { opacity: 0.7 },
});
