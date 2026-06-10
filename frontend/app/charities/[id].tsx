import React, { useCallback, useEffect, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  Image,
  KeyboardAvoidingView,
  Linking,
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
import { SafeAreaView } from "react-native-safe-area-context";
import { Stack, useLocalSearchParams, useRouter } from "expo-router";

import {
  Charity,
  CharityQuoteApi,
  contactCharity,
  getCharity,
  listCharityQuotes,
  requestCharityClaim,
} from "@/src/api";
import { useAuth } from "@/src/auth-context";
import { colors, fonts, radius, shadow, spacing } from "@/src/theme";
import { pickCharityQuote, pickQuoteFromPool } from "@/src/utils/charity-quotes";

export default function CharityDetail() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const router = useRouter();
  const { user } = useAuth();
  const [charity, setCharity] = useState<Charity | null>(null);
  const [loading, setLoading] = useState(true);
  const [interestOpen, setInterestOpen] = useState(false);
  const [claimOpen, setClaimOpen] = useState(false);

  const load = useCallback(async () => {
    if (!id) return;
    setLoading(true);
    try { setCharity(await getCharity(id)); }
    catch (e: any) { Alert.alert("Not found", e?.message || ""); router.back(); }
    finally { setLoading(false); }
  }, [id, router]);

  useEffect(() => { load(); }, [load]);

  if (loading || !charity) {
    return (
      <SafeAreaView style={styles.safe}>
        <Stack.Screen options={{ headerShown: false }} />
        <View style={styles.center}><ActivityIndicator color={colors.primary} /></View>
      </SafeAreaView>
    );
  }

  const openWeb = () => charity.website ? Linking.openURL(charity.website) : null;
  const openEmail = () => charity.email ? Linking.openURL(`mailto:${charity.email}`) : null;
  const openPhone = () => charity.phone ? Linking.openURL(`tel:${charity.phone.replace(/[^0-9+]/g, "")}`) : null;
  const isPending = charity.status === "pending";

  return (
    <SafeAreaView style={styles.safe} edges={["top"]}>
      <Stack.Screen options={{ headerShown: false }} />
      <View style={styles.header}>
        <Pressable onPress={() => router.back()} hitSlop={10} style={styles.headerBtn}>
          <Ionicons name="chevron-back" size={24} color={colors.primary} />
        </Pressable>
        <Text style={styles.headerTitle} numberOfLines={1}>{charity.name}</Text>
        <View style={styles.headerBtn} />
      </View>

      <ScrollView contentContainerStyle={styles.scroll}>
        <View style={styles.heroRow}>
          {charity.logo_url ? (
            <Image source={{ uri: charity.logo_url }} style={styles.logo} resizeMode="cover" />
          ) : (
            <View style={[styles.logo, styles.logoPh]}><Ionicons name="heart-circle-outline" size={36} color={colors.gold} /></View>
          )}
          <View style={{ flex: 1 }}>
            <Text style={styles.name}>{charity.name}</Text>
            <Text style={styles.loc}>{[charity.city, charity.state, charity.country].filter(Boolean).join(", ")}</Text>
            {isPending ? (
              <View style={styles.pendingTag}><Text style={styles.pendingText}>Awaiting admin approval</Text></View>
            ) : null}
          </View>
        </View>

        <Text style={styles.sectionLabel}>Mission</Text>
        <Text style={styles.mission}>{charity.mission}</Text>

        <Text style={styles.sectionLabel}>Get in touch</Text>
        <View style={styles.contactRow}>
          {charity.website ? (
            <Pressable onPress={openWeb} style={({ pressed }) => [styles.contactBtn, pressed && { opacity: 0.7 }]}>
              <Ionicons name="globe-outline" size={18} color={colors.primary} />
              <Text style={styles.contactText}>Website</Text>
            </Pressable>
          ) : null}
          {charity.email ? (
            <Pressable onPress={openEmail} style={({ pressed }) => [styles.contactBtn, pressed && { opacity: 0.7 }]}>
              <Ionicons name="mail-outline" size={18} color={colors.primary} />
              <Text style={styles.contactText}>Email</Text>
            </Pressable>
          ) : null}
          {charity.phone ? (
            <Pressable onPress={openPhone} style={({ pressed }) => [styles.contactBtn, pressed && { opacity: 0.7 }]}>
              <Ionicons name="call-outline" size={18} color={colors.primary} />
              <Text style={styles.contactText}>Call</Text>
            </Pressable>
          ) : null}
        </View>

        {!isPending ? (
          <View style={styles.actionsCol}>
            <Pressable onPress={() => setInterestOpen(true)} style={({ pressed }) => [styles.primaryBtn, pressed && { opacity: 0.8 }]} testID="i-am-interested-btn">
              <Ionicons name="hand-right" size={16} color="#fff" />
              <Text style={styles.primaryBtnText}>I&apos;m interested in volunteering</Text>
            </Pressable>
            {!charity.claimed_by ? (
              <Pressable onPress={() => setClaimOpen(true)} style={({ pressed }) => [styles.ghostBtn, pressed && { opacity: 0.6 }]}>
                <Ionicons name="shield-checkmark-outline" size={16} color={colors.gold} />
                <Text style={styles.ghostBtnText}>I represent this charity · Claim</Text>
              </Pressable>
            ) : null}
          </View>
        ) : null}

        <CharityQuoteCard charityId={charity.charity_id} />
      </ScrollView>

      <InterestModal
        open={interestOpen}
        charity={charity}
        defaultName={user?.name || ""}
        onClose={() => setInterestOpen(false)}
      />
      <ClaimModal
        open={claimOpen}
        charity={charity}
        onClose={() => setClaimOpen(false)}
      />
    </SafeAreaView>
  );
}

function InterestModal({ open, charity, defaultName, onClose }: { open: boolean; charity: Charity; defaultName: string; onClose: () => void }) {
  const [msg, setMsg] = useState("");
  const [sending, setSending] = useState(false);
  const [done, setDone] = useState(false);
  const send = async () => {
    setSending(true);
    try {
      const r = await contactCharity(charity.charity_id, msg.trim() || `Hi, I'm ${defaultName || "a Sanctus member"} and I'd love to volunteer.`);
      setDone(true);
      if (r.charity_email) {
        // also open the user's email client as a fallback
        setTimeout(() => Linking.openURL(`mailto:${r.charity_email}?subject=Volunteer interest — Sanctus&body=${encodeURIComponent(msg)}`).catch(() => {}), 600);
      }
    } catch (e: any) {
      Alert.alert("Couldn't send", e?.message || "");
    } finally { setSending(false); }
  };
  return (
    <Modal visible={open} animationType="slide" presentationStyle="pageSheet" onRequestClose={onClose}>
      <SafeAreaView style={styles.safe} edges={["top"]}>
        <View style={styles.header}>
          <Pressable onPress={onClose} hitSlop={10} style={styles.headerBtn}><Ionicons name="close" size={24} color={colors.primary} /></Pressable>
          <Text style={styles.headerTitle}>{done ? "Sent" : "Volunteer interest"}</Text>
          <View style={styles.headerBtn} />
        </View>
        <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === "ios" ? "padding" : undefined}>
          <ScrollView contentContainerStyle={{ padding: spacing.md, gap: spacing.sm }}>
            {done ? (
              <View style={{ alignItems: "center", paddingVertical: spacing.xl, gap: spacing.md }}>
                <Ionicons name="checkmark-circle" size={64} color={colors.liturgical.green} />
                <Text style={styles.modalTitle}>Thank you for stepping forward.</Text>
                <Text style={styles.modalHint}>{charity.email ? `We've noted your interest and opened your email app so you can reach ${charity.email} directly.` : "We've recorded your interest. We'll forward it to the charity once email delivery is enabled."}</Text>
                <Pressable onPress={onClose} style={({ pressed }) => [styles.primaryBtn, pressed && { opacity: 0.8 }]}><Text style={styles.primaryBtnText}>Done</Text></Pressable>
              </View>
            ) : (
              <>
                <Text style={styles.modalHint}>Tell {charity.name} a little about how you&apos;d like to help. We&apos;ll record your interest and notify them.</Text>
                <TextInput value={msg} onChangeText={setMsg} placeholder={`Hi, I'd love to volunteer with ${charity.name}. I have time on weekends...`} placeholderTextColor={colors.textMuted} style={[styles.input, { minHeight: 120 }]} multiline />
                <Pressable onPress={send} disabled={sending} style={({ pressed }) => [styles.primaryBtn, pressed && { opacity: 0.8 }, sending && { opacity: 0.6 }]}>
                  {sending ? <ActivityIndicator color="#fff" /> : <><Ionicons name="send" size={16} color="#fff" /><Text style={styles.primaryBtnText}>Send interest</Text></>}
                </Pressable>
              </>
            )}
          </ScrollView>
        </KeyboardAvoidingView>
      </SafeAreaView>
    </Modal>
  );
}

function ClaimModal({ open, charity, onClose }: { open: boolean; charity: Charity; onClose: () => void }) {
  const [msg, setMsg] = useState("");
  const [sending, setSending] = useState(false);
  const [done, setDone] = useState(false);
  const send = async () => {
    setSending(true);
    try {
      await requestCharityClaim(charity.charity_id, msg.trim());
      setDone(true);
    } catch (e: any) {
      Alert.alert("Couldn't send", e?.message || "");
    } finally { setSending(false); }
  };
  return (
    <Modal visible={open} animationType="slide" presentationStyle="pageSheet" onRequestClose={onClose}>
      <SafeAreaView style={styles.safe} edges={["top"]}>
        <View style={styles.header}>
          <Pressable onPress={onClose} hitSlop={10} style={styles.headerBtn}><Ionicons name="close" size={24} color={colors.primary} /></Pressable>
          <Text style={styles.headerTitle}>{done ? "Request sent" : "Claim this charity"}</Text>
          <View style={styles.headerBtn} />
        </View>
        <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === "ios" ? "padding" : undefined}>
          <ScrollView contentContainerStyle={{ padding: spacing.md, gap: spacing.sm }}>
            {done ? (
              <View style={{ alignItems: "center", paddingVertical: spacing.xl, gap: spacing.md }}>
                <Ionicons name="shield-checkmark" size={64} color={colors.liturgical.green} />
                <Text style={styles.modalTitle}>Claim request received.</Text>
                <Text style={styles.modalHint}>Our team will verify your role and reach out at the email on your Sanctus account.</Text>
                <Pressable onPress={onClose} style={({ pressed }) => [styles.primaryBtn, pressed && { opacity: 0.8 }]}><Text style={styles.primaryBtnText}>Done</Text></Pressable>
              </View>
            ) : (
              <>
                <Text style={styles.modalHint}>Tell us who you are at {charity.name} (e.g. &ldquo;I&apos;m the volunteer coordinator&rdquo;) and how we can verify your role. An admin will review.</Text>
                <TextInput value={msg} onChangeText={setMsg} placeholder="I'm the volunteer coordinator. You can verify via our website's staff page or by emailing info@..." placeholderTextColor={colors.textMuted} style={[styles.input, { minHeight: 120 }]} multiline />
                <Pressable onPress={send} disabled={sending} style={({ pressed }) => [styles.primaryBtn, pressed && { opacity: 0.8 }, sending && { opacity: 0.6 }]}>
                  {sending ? <ActivityIndicator color="#fff" /> : <><Ionicons name="send" size={16} color="#fff" /><Text style={styles.primaryBtnText}>Submit claim</Text></>}
                </Pressable>
              </>
            )}
          </ScrollView>
        </KeyboardAvoidingView>
      </SafeAreaView>
    </Modal>
  );
}

/** Reverent quote card on the Charity detail page — pulls admin-curated
 * Catholic teachings on charity from the API, falling back to the bundled
 * static pool when offline or the request fails. Tap "Another" to draw a
 * different quote. Stable per-charity on first render. */
function CharityQuoteCard({ charityId }: { charityId: string }) {
  const [seed, setSeed] = useState<string>(charityId);
  const [pool, setPool] = useState<CharityQuoteApi[] | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const r = await listCharityQuotes();
        if (!cancelled) setPool(r.items || []);
      } catch {
        if (!cancelled) setPool([]); // signal failure → fallback below
      }
    })();
    return () => { cancelled = true; };
  }, []);

  // Prefer the admin-curated pool; if it's empty or the fetch failed, fall
  // back to the bundled static list so we never render an empty card.
  const fromApi = pool && pool.length > 0 ? pickQuoteFromPool(pool, seed) : null;
  const quote = fromApi ?? pickCharityQuote(seed);

  const shuffle = () => setSeed(`${charityId}-${Date.now()}-${Math.random()}`);
  return (
    <View testID="charity-quote-card" style={styles.quoteCard}>
      <View style={styles.quoteOrnamentRow}>
        <View style={styles.quoteRule} />
        <Ionicons name="rose-outline" size={14} color={colors.gold} />
        <View style={styles.quoteRule} />
      </View>
      <Text style={styles.quoteLabel}>From the saints on charity</Text>
      <Text style={styles.quoteOpen}>&ldquo;</Text>
      <Text style={styles.quoteText}>{quote.text}</Text>
      <Text style={styles.quoteAttrib}>— {quote.source}</Text>
      {quote.context ? (
        <Text style={styles.quoteContext}>{quote.context}</Text>
      ) : null}
      <Pressable
        testID="charity-quote-shuffle"
        onPress={shuffle}
        hitSlop={10}
        style={({ pressed }) => [styles.quoteShuffle, pressed && { opacity: 0.6 }]}
      >
        <Ionicons name="refresh" size={14} color={colors.gold} />
        <Text style={styles.quoteShuffleText}>Another</Text>
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.background },
  header: { flexDirection: "row", alignItems: "center", paddingHorizontal: spacing.md, paddingVertical: spacing.sm, borderBottomWidth: StyleSheet.hairlineWidth, borderBottomColor: colors.border, backgroundColor: colors.surface },
  headerBtn: { padding: spacing.xs, width: 44, alignItems: "center" },
  headerTitle: { flex: 1, textAlign: "center", fontFamily: fonts.uiSemi, fontSize: 15, color: colors.primary },
  center: { flex: 1, alignItems: "center", justifyContent: "center" },
  scroll: { padding: spacing.md, paddingBottom: spacing.xl, gap: spacing.sm },
  heroRow: { flexDirection: "row", gap: spacing.sm, alignItems: "center" },
  logo: { width: 80, height: 80, borderRadius: radius.lg, backgroundColor: colors.surface },
  logoPh: { alignItems: "center", justifyContent: "center" },
  name: { fontFamily: fonts.headingBold, fontSize: 22, color: colors.primary },
  loc: { fontFamily: fonts.uiMedium, fontSize: 13, color: colors.textMuted, marginTop: 2 },
  pendingTag: { alignSelf: "flex-start", marginTop: 6, paddingHorizontal: 8, paddingVertical: 3, borderRadius: radius.round, backgroundColor: colors.gold + "22", borderWidth: 1, borderColor: colors.gold },
  pendingText: { fontFamily: fonts.uiSemi, fontSize: 11, color: colors.gold },
  sectionLabel: { marginTop: spacing.md, fontFamily: fonts.uiSemi, fontSize: 11, color: colors.textMuted, textTransform: "uppercase" },
  mission: { fontFamily: fonts.bodyRegular, fontSize: 15, color: colors.textSecondary, lineHeight: 22 },
  contactRow: { flexDirection: "row", gap: 8, flexWrap: "wrap" },
  contactBtn: { flexDirection: "row", alignItems: "center", gap: 6, paddingHorizontal: 14, paddingVertical: 10, borderRadius: radius.round, backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.borderSoft, ...shadow.card },
  contactText: { fontFamily: fonts.uiSemi, fontSize: 13, color: colors.primary },
  actionsCol: { marginTop: spacing.lg, gap: spacing.sm },
  primaryBtn: { flexDirection: "row", alignItems: "center", justifyContent: "center", gap: 8, paddingVertical: 13, borderRadius: radius.round, backgroundColor: colors.primary },
  primaryBtnText: { fontFamily: fonts.uiSemi, fontSize: 14, color: "#fff" },
  ghostBtn: { flexDirection: "row", alignItems: "center", justifyContent: "center", gap: 8, paddingVertical: 12, borderRadius: radius.round, borderWidth: 1, borderColor: colors.gold + "66", backgroundColor: colors.gold + "11" },
  ghostBtnText: { fontFamily: fonts.uiSemi, fontSize: 13, color: colors.gold },
  modalTitle: { fontFamily: fonts.headingBold, fontSize: 20, color: colors.primary, textAlign: "center" },
  modalHint: { fontFamily: fonts.bodyRegular, fontSize: 14, color: colors.textSecondary, lineHeight: 20, textAlign: "center" },
  input: { borderWidth: 1, borderColor: colors.border, borderRadius: radius.md, padding: 12, fontFamily: fonts.bodyRegular, fontSize: 14, color: colors.textPrimary, backgroundColor: colors.surface, textAlignVertical: "top" },

  // Quote card (bottom of detail page)
  quoteCard: {
    marginTop: spacing.xl,
    marginBottom: spacing.lg,
    paddingHorizontal: spacing.lg,
    paddingTop: spacing.lg,
    paddingBottom: spacing.md,
    backgroundColor: colors.surface,
    borderRadius: radius.lg,
    borderWidth: 1,
    borderColor: colors.gold + "33",
    alignItems: "center",
    ...shadow.card,
  },
  quoteOrnamentRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
    width: "60%",
    marginBottom: spacing.xs,
  },
  quoteRule: {
    flex: 1,
    height: 1,
    backgroundColor: colors.gold + "55",
  },
  quoteLabel: {
    fontFamily: fonts.uiSemi,
    fontSize: 10,
    letterSpacing: 1.5,
    textTransform: "uppercase",
    color: colors.gold,
    marginBottom: spacing.sm,
    textAlign: "center",
  },
  quoteOpen: {
    fontFamily: fonts.headingBold,
    fontSize: 42,
    lineHeight: 42,
    color: colors.gold,
    marginBottom: -8,
  },
  quoteText: {
    fontFamily: fonts.bodyItalic,
    fontSize: 16,
    lineHeight: 24,
    color: colors.textPrimary,
    textAlign: "center",
    paddingHorizontal: spacing.xs,
  },
  quoteAttrib: {
    marginTop: spacing.sm,
    fontFamily: fonts.uiSemi,
    fontSize: 13,
    color: colors.primary,
    textAlign: "center",
  },
  quoteContext: {
    marginTop: 2,
    fontFamily: fonts.uiMedium,
    fontSize: 11,
    color: colors.textMuted,
    textAlign: "center",
  },
  quoteShuffle: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    marginTop: spacing.md,
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: radius.round,
    borderWidth: 1,
    borderColor: colors.gold + "55",
    backgroundColor: colors.gold + "0F",
  },
  quoteShuffleText: {
    fontFamily: fonts.uiSemi,
    fontSize: 11,
    color: colors.gold,
    letterSpacing: 0.5,
  },
});
