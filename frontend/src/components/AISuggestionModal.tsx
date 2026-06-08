import React, { useEffect, useState } from "react";
import {
  ActivityIndicator,
  KeyboardAvoidingView,
  Modal,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { colors, fonts, radius, shadow, spacing } from "@/src/theme";

const MAX_LEN = 600;

export interface AISuggestionModalProps {
  visible: boolean;
  title: string;            // e.g. "Talk to the AI about today's meals"
  subtitle?: string;         // a sentence explaining what happens
  initialValue?: string;     // current note for the day, if any
  placeholder?: string;
  examples?: string[];       // chips
  submitting?: boolean;
  onClose: () => void;
  onSubmit: (note: string) => void | Promise<void>;
}

export default function AISuggestionModal({
  visible,
  title,
  subtitle,
  initialValue,
  placeholder,
  examples,
  submitting,
  onClose,
  onSubmit,
}: AISuggestionModalProps) {
  const [text, setText] = useState(initialValue || "");

  // Reset the input when the modal is (re)opened with a different initial value
  useEffect(() => {
    if (visible) setText(initialValue || "");
  }, [visible, initialValue]);

  const trimmed = text.trim();
  const canSubmit = trimmed.length > 0 && !submitting;

  const insertExample = (ex: string) => {
    // Always replace - examples are alternatives, not additions
    setText(ex);
  };

  const handleSubmit = async () => {
    if (!canSubmit) return;
    await onSubmit(trimmed.slice(0, MAX_LEN));
  };

  return (
    <Modal
      visible={visible}
      animationType="slide"
      transparent
      statusBarTranslucent
      onRequestClose={onClose}
    >
      <View style={styles.backdrop}>
        <Pressable
          style={styles.backdropPress}
          onPress={submitting ? undefined : onClose}
          accessibilityLabel="Dismiss"
        />
        <KeyboardAvoidingView
          behavior={Platform.OS === "ios" ? "padding" : undefined}
          style={styles.sheetWrap}
          pointerEvents="box-none"
        >
          <View style={styles.sheet} testID="ai-suggestion-modal">
            <View style={styles.grabber} />

            <View style={styles.headerRow}>
              <View style={{ flex: 1 }}>
                <Text style={styles.title}>{title}</Text>
                {subtitle ? <Text style={styles.subtitle}>{subtitle}</Text> : null}
              </View>
              <Pressable
                onPress={onClose}
                hitSlop={12}
                disabled={submitting}
                testID="ai-suggestion-close"
              >
                <Ionicons name="close" size={22} color={colors.textMuted} />
              </Pressable>
            </View>

            <View style={styles.inputWrap}>
              <TextInput
                value={text}
                onChangeText={(t) => setText(t.slice(0, MAX_LEN))}
                placeholder={placeholder || "Type your request to the AI…"}
                placeholderTextColor={colors.textMuted}
                multiline
                style={styles.input}
                editable={!submitting}
                testID="ai-suggestion-input"
                autoFocus
              />
              <Text style={styles.counter}>{text.length}/{MAX_LEN}</Text>
            </View>

            {examples && examples.length > 0 ? (
              <View style={styles.examplesWrap}>
                <Text style={styles.examplesLabel}>QUICK IDEAS</Text>
                <ScrollView
                  horizontal
                  showsHorizontalScrollIndicator={false}
                  contentContainerStyle={styles.examplesRow}
                >
                  {examples.map((ex, i) => (
                    <Pressable
                      key={i}
                      onPress={() => insertExample(ex)}
                      disabled={submitting}
                      style={({ pressed }) => [styles.exChip, pressed && styles.pressed]}
                      testID={`ai-suggestion-example-${i}`}
                    >
                      <Text style={styles.exChipText} numberOfLines={2}>{ex}</Text>
                    </Pressable>
                  ))}
                </ScrollView>
              </View>
            ) : null}

            <View style={styles.actionRow}>
              <Pressable
                onPress={onClose}
                disabled={submitting}
                style={({ pressed }) => [styles.secondaryBtn, pressed && styles.pressed]}
                testID="ai-suggestion-cancel"
              >
                <Text style={styles.secondaryBtnText}>Cancel</Text>
              </Pressable>
              <Pressable
                onPress={handleSubmit}
                disabled={!canSubmit}
                style={({ pressed }) => [
                  styles.primaryBtn,
                  !canSubmit && styles.primaryBtnDisabled,
                  pressed && canSubmit && styles.pressed,
                ]}
                testID="ai-suggestion-submit"
              >
                {submitting ? (
                  <ActivityIndicator color={colors.gold} />
                ) : (
                  <>
                    <Ionicons name="sparkles" size={16} color={colors.gold} />
                    <Text style={styles.primaryBtnText}>Generate with this note</Text>
                  </>
                )}
              </Pressable>
            </View>
          </View>
        </KeyboardAvoidingView>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  backdrop: {
    flex: 1,
    backgroundColor: "rgba(28, 40, 65, 0.45)",
    justifyContent: "flex-end",
  },
  backdropPress: { ...StyleSheet.absoluteFillObject },
  sheetWrap: { width: "100%" },
  sheet: {
    backgroundColor: colors.surface,
    borderTopLeftRadius: 24,
    borderTopRightRadius: 24,
    paddingHorizontal: spacing.lg,
    paddingTop: spacing.sm,
    paddingBottom: Platform.OS === "ios" ? spacing.xxl : spacing.xl,
    ...shadow.card,
  },
  grabber: {
    alignSelf: "center",
    width: 40,
    height: 4,
    borderRadius: 2,
    backgroundColor: colors.border,
    marginBottom: spacing.md,
  },
  headerRow: {
    flexDirection: "row",
    alignItems: "flex-start",
    gap: spacing.md,
    marginBottom: spacing.md,
  },
  title: {
    fontFamily: fonts.headingBold,
    fontSize: 20,
    color: colors.textPrimary,
  },
  subtitle: {
    fontFamily: fonts.bodyRegular,
    fontSize: 13,
    color: colors.textSecondary,
    marginTop: 4,
    lineHeight: 18,
  },
  inputWrap: {
    backgroundColor: colors.borderSoft,
    borderRadius: radius.md,
    paddingHorizontal: spacing.md,
    paddingTop: spacing.md,
    paddingBottom: spacing.sm,
  },
  input: {
    minHeight: 84,
    maxHeight: 160,
    fontFamily: fonts.bodyRegular,
    fontSize: 15,
    color: colors.textPrimary,
    textAlignVertical: "top",
    padding: 0,
  },
  counter: {
    fontFamily: fonts.uiMedium,
    fontSize: 11,
    color: colors.textMuted,
    textAlign: "right",
    marginTop: 4,
  },
  examplesWrap: { marginTop: spacing.md },
  examplesLabel: {
    fontFamily: fonts.uiSemi,
    fontSize: 11,
    letterSpacing: 1.5,
    color: colors.gold,
    marginBottom: spacing.xs,
  },
  examplesRow: { gap: spacing.sm, paddingRight: spacing.md },
  exChip: {
    paddingHorizontal: spacing.md,
    paddingVertical: 8,
    borderRadius: radius.round,
    borderWidth: 1,
    borderColor: colors.border,
    backgroundColor: colors.surface,
    maxWidth: 260,
  },
  exChipText: {
    fontFamily: fonts.bodyRegular,
    fontSize: 13,
    color: colors.textPrimary,
  },
  actionRow: {
    flexDirection: "row",
    gap: spacing.sm,
    marginTop: spacing.lg,
  },
  secondaryBtn: {
    flex: 1,
    paddingVertical: 14,
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: colors.border,
    alignItems: "center",
    justifyContent: "center",
  },
  secondaryBtnText: {
    fontFamily: fonts.uiSemi,
    fontSize: 14,
    color: colors.textPrimary,
  },
  primaryBtn: {
    flex: 1.4,
    paddingVertical: 14,
    borderRadius: radius.md,
    backgroundColor: colors.primary,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: spacing.sm,
  },
  primaryBtnDisabled: {
    opacity: 0.5,
  },
  primaryBtnText: {
    fontFamily: fonts.uiSemi,
    color: colors.gold,
    fontSize: 14,
    letterSpacing: 0.4,
  },
  pressed: { opacity: 0.7 },
});
