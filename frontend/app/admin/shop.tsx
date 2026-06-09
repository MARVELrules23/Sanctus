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
import * as ImagePicker from "expo-image-picker";
import { Ionicons } from "@expo/vector-icons";
import { SafeAreaView } from "react-native-safe-area-context";
import { Stack, useRouter } from "expo-router";

import {
  ShopOrder,
  ShopProduct,
  adminArchiveProduct,
  adminCreateProduct,
  adminListOrders,
  adminListProducts,
  adminSetOrderTracking,
  adminUpdateProduct,
} from "@/src/api";
import { useAuth } from "@/src/auth-context";
import { colors, fonts, radius, shadow, spacing } from "@/src/theme";

type Tab = "products" | "orders";

type ProductDraft = {
  product_id?: string;
  name: string;
  description: string;
  price_dollars: string;
  stock: string;
  image_url: string | null;
  status?: "active" | "archived";
};

const EMPTY_DRAFT: ProductDraft = {
  name: "",
  description: "",
  price_dollars: "",
  stock: "",
  image_url: null,
};

function formatPrice(cents?: number): string {
  if (cents == null) return "";
  return `$${(cents / 100).toFixed(2)}`;
}

function parseDollars(s: string): number {
  const n = Number((s || "").trim());
  if (!isFinite(n) || n <= 0) return 0;
  return Math.round(n * 100);
}

export default function AdminShopScreen() {
  const router = useRouter();
  const { user } = useAuth();
  const [tab, setTab] = useState<Tab>("products");
  const [products, setProducts] = useState<ShopProduct[]>([]);
  const [orders, setOrders] = useState<ShopOrder[]>([]);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState<ProductDraft | null>(null);
  const [orderEditing, setOrderEditing] = useState<ShopOrder | null>(null);

  const load = useCallback(async () => {
    if (!user?.is_admin) return;
    setLoading(true);
    try {
      const [p, o] = await Promise.all([adminListProducts(), adminListOrders()]);
      setProducts(p.products);
      setOrders(o.orders);
    } catch (e) {
      console.warn("admin shop load failed", e);
    } finally {
      setLoading(false);
    }
  }, [user]);

  useEffect(() => { load(); }, [load]);

  if (!user?.is_admin) {
    return (
      <SafeAreaView style={styles.safe}>
        <Stack.Screen options={{ headerShown: false }} />
        <View style={styles.center}>
          <Text style={styles.gateText}>Admins only.</Text>
        </View>
      </SafeAreaView>
    );
  }

  const openNew = () => setEditing({ ...EMPTY_DRAFT });
  const openEdit = (p: ShopProduct) =>
    setEditing({
      product_id: p.product_id,
      name: p.name,
      description: p.description || "",
      price_dollars: (p.price_cents / 100).toString(),
      stock: typeof p.stock === "number" ? String(p.stock) : "",
      image_url: p.image_url || null,
      status: p.status,
    });

  return (
    <SafeAreaView style={styles.safe} edges={["top"]}>
      <Stack.Screen options={{ headerShown: false }} />
      <View style={styles.header}>
        <Pressable onPress={() => router.back()} hitSlop={10} style={styles.headerBtn}>
          <Ionicons name="chevron-back" size={24} color={colors.primary} />
        </Pressable>
        <Text style={styles.headerTitle}>Shop · Admin</Text>
        <Pressable onPress={openNew} hitSlop={10} style={styles.headerBtn}>
          <Ionicons name="add-circle" size={26} color={colors.primary} />
        </Pressable>
      </View>

      <View style={styles.tabs}>
        {(["products", "orders"] as Tab[]).map((t) => (
          <Pressable
            key={t}
            onPress={() => setTab(t)}
            style={({ pressed }) => [styles.tab, tab === t && styles.tabActive, pressed && { opacity: 0.7 }]}
          >
            <Text style={[styles.tabText, tab === t && styles.tabTextActive]}>
              {t === "products" ? `Products (${products.length})` : `Orders (${orders.length})`}
            </Text>
          </Pressable>
        ))}
      </View>

      {loading ? (
        <View style={styles.center}><ActivityIndicator color={colors.primary} /></View>
      ) : (
        <ScrollView contentContainerStyle={styles.list}>
          {tab === "products" ? (
            products.length === 0 ? (
              <Text style={styles.empty}>No products yet — tap + to create your first listing.</Text>
            ) : (
              products.map((p) => (
                <Pressable key={p.product_id} onPress={() => openEdit(p)} style={({ pressed }) => [styles.row, pressed && { opacity: 0.85 }]}>
                  {p.image_url ? (
                    <Image source={{ uri: p.image_url }} style={styles.thumb} resizeMode="cover" />
                  ) : (
                    <View style={[styles.thumb, styles.thumbPh]}><Ionicons name="image-outline" size={22} color={colors.textMuted} /></View>
                  )}
                  <View style={{ flex: 1 }}>
                    <Text style={styles.rowName} numberOfLines={1}>{p.name}</Text>
                    <Text style={styles.rowMeta}>{formatPrice(p.price_cents)}{typeof p.stock === "number" ? ` · ${p.stock} in stock` : ""}</Text>
                  </View>
                  {p.status === "archived" ? (
                    <Text style={styles.archivedTag}>Archived</Text>
                  ) : (
                    <Ionicons name="chevron-forward" size={18} color={colors.textMuted} />
                  )}
                </Pressable>
              ))
            )
          ) : orders.length === 0 ? (
            <Text style={styles.empty}>No orders yet.</Text>
          ) : (
            orders.map((o) => (
              <Pressable key={o.order_id} onPress={() => setOrderEditing(o)} style={({ pressed }) => [styles.row, pressed && { opacity: 0.85 }]}>
                {o.product_image_url ? (
                  <Image source={{ uri: o.product_image_url }} style={styles.thumb} resizeMode="cover" />
                ) : (
                  <View style={[styles.thumb, styles.thumbPh]}><Ionicons name="cube-outline" size={22} color={colors.textMuted} /></View>
                )}
                <View style={{ flex: 1 }}>
                  <Text style={styles.rowName} numberOfLines={1}>{o.product_name || o.product_id}</Text>
                  <Text style={styles.rowMeta}>{o.customer_email} · {formatPrice(o.total_cents)} · {o.status}</Text>
                  {o.tracking_number ? <Text style={styles.tracking}>Track: {o.tracking_number}</Text> : null}
                </View>
                <Ionicons name="chevron-forward" size={18} color={colors.textMuted} />
              </Pressable>
            ))
          )}
        </ScrollView>
      )}

      <ProductEditorModal
        open={!!editing}
        draft={editing}
        onClose={() => setEditing(null)}
        onSaved={() => { setEditing(null); load(); }}
      />

      <TrackingModal
        open={!!orderEditing}
        order={orderEditing}
        onClose={() => setOrderEditing(null)}
        onSaved={() => { setOrderEditing(null); load(); }}
      />
    </SafeAreaView>
  );
}

function ProductEditorModal({
  open,
  draft,
  onClose,
  onSaved,
}: {
  open: boolean;
  draft: ProductDraft | null;
  onClose: () => void;
  onSaved: () => void;
}) {
  const [d, setD] = useState<ProductDraft | null>(draft);
  const [saving, setSaving] = useState(false);
  const [picking, setPicking] = useState(false);

  useEffect(() => { setD(draft); }, [draft]);
  if (!open || !d) return null;

  const set = <K extends keyof ProductDraft>(k: K, v: ProductDraft[K]) => setD({ ...d, [k]: v });

  const pickImage = async () => {
    if (picking) return;
    setPicking(true);
    try {
      const perm = await ImagePicker.getMediaLibraryPermissionsAsync();
      let status = perm.status;
      let canAskAgain = perm.canAskAgain;
      if (status !== "granted") {
        if (canAskAgain) {
          const r = await ImagePicker.requestMediaLibraryPermissionsAsync();
          status = r.status; canAskAgain = r.canAskAgain;
        }
      }
      if (status !== "granted") {
        if (!canAskAgain) {
          Alert.alert("Photos permission needed", "Sanctus needs access to your photos to attach product images.", [
            { text: "Cancel", style: "cancel" },
            { text: "Open Settings", onPress: () => Linking.openSettings() },
          ]);
        }
        return;
      }
      const result = await ImagePicker.launchImageLibraryAsync({
        mediaTypes: ImagePicker.MediaTypeOptions.Images,
        allowsEditing: true,
        aspect: [1, 1],
        quality: 0.72,
        base64: true,
      });
      if (result.canceled || !result.assets?.length) return;
      const a = result.assets[0];
      let uri = a.uri;
      if (a.base64) uri = `data:${a.mimeType || "image/jpeg"};base64,${a.base64}`;
      if (uri.startsWith("data:") && uri.length > 2_800_000) {
        Alert.alert("Image too large", "Please pick a smaller photo (max ~2 MB).");
        return;
      }
      set("image_url", uri);
    } catch (e) {
      console.warn("pick image failed", e);
    } finally {
      setPicking(false);
    }
  };

  const save = async () => {
    if (!d) return;
    const name = (d.name || "").trim();
    if (name.length < 2) { Alert.alert("Name required", "Give the product a name."); return; }
    const cents = parseDollars(d.price_dollars);
    if (cents < 100) { Alert.alert("Invalid price", "Price must be at least $1."); return; }
    const stock = d.stock.trim() === "" ? null : Math.max(0, Number(d.stock));
    if (stock !== null && (!isFinite(stock as number) || (stock as number) < 0)) {
      Alert.alert("Invalid stock", "Stock must be a non-negative number."); return;
    }
    setSaving(true);
    try {
      if (d.product_id) {
        await adminUpdateProduct(d.product_id, {
          name,
          description: d.description,
          price_cents: cents,
          image_url: d.image_url,
          stock: stock as number | null,
          status: d.status,
        });
      } else {
        await adminCreateProduct({
          name,
          description: d.description,
          price_cents: cents,
          image_url: d.image_url,
          stock: stock as number | null,
        });
      }
      onSaved();
    } catch (e: any) {
      Alert.alert("Save failed", e?.message || "Try again.");
    } finally {
      setSaving(false);
    }
  };

  const archive = async () => {
    if (!d.product_id) return;
    Alert.alert("Archive product?", "It will be hidden from the shop. Existing orders are unaffected.", [
      { text: "Cancel", style: "cancel" },
      { text: "Archive", style: "destructive", onPress: async () => {
        try { await adminArchiveProduct(d.product_id!); onSaved(); } catch (e: any) { Alert.alert("Failed", e?.message || ""); }
      }},
    ]);
  };

  return (
    <Modal visible={open} animationType="slide" onRequestClose={onClose} presentationStyle="pageSheet">
      <SafeAreaView style={styles.safe} edges={["top"]}>
        <View style={styles.header}>
          <Pressable onPress={onClose} hitSlop={10} style={styles.headerBtn}>
            <Ionicons name="close" size={24} color={colors.primary} />
          </Pressable>
          <Text style={styles.headerTitle}>{d.product_id ? "Edit product" : "New product"}</Text>
          <Pressable onPress={save} disabled={saving} hitSlop={10} style={styles.headerBtn}>
            {saving ? <ActivityIndicator color={colors.primary} /> : <Text style={styles.saveText}>Save</Text>}
          </Pressable>
        </View>
        <KeyboardAvoidingView behavior={Platform.OS === "ios" ? "padding" : undefined} style={{ flex: 1 }}>
          <ScrollView contentContainerStyle={{ padding: spacing.md, gap: spacing.sm, paddingBottom: spacing.xl }}>
            <Text style={styles.label}>Image</Text>
            {d.image_url ? (
              <View style={styles.previewWrap}>
                <Image source={{ uri: d.image_url }} style={styles.previewImg} resizeMode="cover" />
                <Pressable onPress={() => set("image_url", null)} style={styles.previewClear} hitSlop={8}>
                  <Ionicons name="close" size={16} color="#fff" />
                </Pressable>
              </View>
            ) : null}
            <Pressable onPress={pickImage} disabled={picking} style={({ pressed }) => [styles.pickerBtn, pressed && { opacity: 0.8 }]}>
              {picking ? <ActivityIndicator size="small" color={colors.primary} /> : <Ionicons name="image-outline" size={16} color={colors.primary} />}
              <Text style={styles.pickerBtnText}>{picking ? "Loading…" : d.image_url ? "Replace from library" : "Upload from library"}</Text>
            </Pressable>

            <Text style={styles.label}>Name</Text>
            <TextInput value={d.name} onChangeText={(v) => set("name", v)} style={styles.input} placeholder="Wooden rosary" placeholderTextColor={colors.textMuted} />

            <Text style={styles.label}>Description</Text>
            <TextInput value={d.description} onChangeText={(v) => set("description", v)} style={[styles.input, { minHeight: 80 }]} multiline placeholder="Hand-carved olive wood beads, blessed at Sanctus HQ." placeholderTextColor={colors.textMuted} />

            <Text style={styles.label}>Price (USD)</Text>
            <TextInput value={d.price_dollars} onChangeText={(v) => set("price_dollars", v.replace(/[^0-9.]/g, ""))} style={styles.input} placeholder="29.99" placeholderTextColor={colors.textMuted} keyboardType="decimal-pad" />

            <Text style={styles.label}>Stock (optional)</Text>
            <TextInput value={d.stock} onChangeText={(v) => set("stock", v.replace(/[^0-9]/g, ""))} style={styles.input} placeholder="Leave blank for unlimited" placeholderTextColor={colors.textMuted} keyboardType="number-pad" />

            <Text style={styles.note}>Flat $5 shipping (US) is added automatically at checkout.</Text>

            {d.product_id ? (
              <Pressable onPress={archive} style={({ pressed }) => [styles.archiveBtn, pressed && { opacity: 0.7 }]}>
                <Ionicons name="archive-outline" size={16} color={colors.liturgical.red} />
                <Text style={styles.archiveText}>Archive product</Text>
              </Pressable>
            ) : null}
          </ScrollView>
        </KeyboardAvoidingView>
      </SafeAreaView>
    </Modal>
  );
}

function TrackingModal({
  open, order, onClose, onSaved,
}: { open: boolean; order: ShopOrder | null; onClose: () => void; onSaved: () => void }) {
  const [tracking, setTracking] = useState("");
  const [saving, setSaving] = useState(false);
  useEffect(() => { setTracking(order?.tracking_number || ""); }, [order]);
  if (!open || !order) return null;
  const save = async () => {
    if (!tracking.trim()) { Alert.alert("Tracking required", "Enter a tracking number."); return; }
    setSaving(true);
    try { await adminSetOrderTracking(order.order_id, tracking.trim()); onSaved(); }
    catch (e: any) { Alert.alert("Failed", e?.message || ""); }
    finally { setSaving(false); }
  };
  return (
    <Modal visible={open} animationType="slide" onRequestClose={onClose} presentationStyle="pageSheet">
      <SafeAreaView style={styles.safe} edges={["top"]}>
        <View style={styles.header}>
          <Pressable onPress={onClose} hitSlop={10} style={styles.headerBtn}><Ionicons name="close" size={24} color={colors.primary} /></Pressable>
          <Text style={styles.headerTitle}>Order details</Text>
          <Pressable onPress={save} disabled={saving} hitSlop={10} style={styles.headerBtn}>
            {saving ? <ActivityIndicator color={colors.primary} /> : <Text style={styles.saveText}>Save</Text>}
          </Pressable>
        </View>
        <ScrollView contentContainerStyle={{ padding: spacing.md, gap: spacing.sm }}>
          <Text style={styles.label}>Product</Text>
          <Text style={styles.value}>{order.product_name}</Text>
          <Text style={styles.label}>Customer</Text>
          <Text style={styles.value}>{order.customer_email || "(no email)"}</Text>
          <Text style={styles.label}>Total</Text>
          <Text style={styles.value}>{formatPrice(order.total_cents)} ({order.quantity} × {formatPrice(order.unit_amount_cents)} + {formatPrice(order.shipping_amount_cents)} shipping)</Text>
          <Text style={styles.label}>Status</Text>
          <Text style={styles.value}>{order.status}</Text>
          {order.shipping_details ? (
            <>
              <Text style={styles.label}>Shipping address</Text>
              <Text style={styles.value}>{JSON.stringify((order.shipping_details as any).address || order.shipping_details, null, 2)}</Text>
            </>
          ) : null}
          <Text style={styles.label}>Tracking number</Text>
          <TextInput value={tracking} onChangeText={setTracking} style={styles.input} placeholder="USPS / UPS tracking #" placeholderTextColor={colors.textMuted} autoCapitalize="characters" />
        </ScrollView>
      </SafeAreaView>
    </Modal>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.background },
  header: { flexDirection: "row", alignItems: "center", paddingHorizontal: spacing.md, paddingVertical: spacing.sm, borderBottomWidth: StyleSheet.hairlineWidth, borderBottomColor: colors.border, backgroundColor: colors.surface },
  headerBtn: { padding: spacing.xs, width: 44, alignItems: "center" },
  headerTitle: { flex: 1, textAlign: "center", fontFamily: fonts.headingBold, fontSize: 20, color: colors.primary },
  saveText: { fontFamily: fonts.uiSemi, fontSize: 14, color: colors.primary },
  tabs: { flexDirection: "row", padding: spacing.sm, gap: 8, backgroundColor: colors.surface, borderBottomWidth: StyleSheet.hairlineWidth, borderBottomColor: colors.border },
  tab: { flex: 1, paddingVertical: 8, borderRadius: radius.round, alignItems: "center", backgroundColor: colors.background },
  tabActive: { backgroundColor: colors.primary },
  tabText: { fontFamily: fonts.uiSemi, fontSize: 12, color: colors.textSecondary },
  tabTextActive: { color: "#fff" },
  list: { padding: spacing.md, gap: spacing.sm },
  empty: { textAlign: "center", color: colors.textMuted, fontFamily: fonts.bodyRegular, fontSize: 14, paddingVertical: spacing.xl },
  row: { flexDirection: "row", alignItems: "center", gap: spacing.sm, padding: spacing.sm, backgroundColor: colors.surface, borderRadius: radius.lg, ...shadow.card, marginBottom: spacing.sm },
  thumb: { width: 52, height: 52, borderRadius: radius.md, backgroundColor: colors.background },
  thumbPh: { alignItems: "center", justifyContent: "center" },
  rowName: { fontFamily: fonts.uiSemi, fontSize: 14, color: colors.textPrimary },
  rowMeta: { fontFamily: fonts.uiMedium, fontSize: 12, color: colors.textSecondary, marginTop: 2 },
  tracking: { fontFamily: fonts.uiMedium, fontSize: 11, color: colors.primary, marginTop: 2 },
  archivedTag: { fontFamily: fonts.uiSemi, fontSize: 11, color: colors.textMuted, paddingHorizontal: 8, paddingVertical: 3, borderRadius: radius.round, backgroundColor: colors.background, borderWidth: 1, borderColor: colors.border },
  label: { marginTop: spacing.sm, fontFamily: fonts.uiSemi, fontSize: 11, color: colors.textMuted, textTransform: "uppercase" },
  value: { fontFamily: fonts.bodyRegular, fontSize: 14, color: colors.textPrimary },
  input: { borderWidth: 1, borderColor: colors.border, borderRadius: radius.md, padding: 12, fontFamily: fonts.bodyRegular, fontSize: 14, color: colors.textPrimary, backgroundColor: colors.surface },
  note: { marginTop: spacing.sm, fontFamily: fonts.uiMedium, fontSize: 12, color: colors.textMuted },
  archiveBtn: { flexDirection: "row", alignItems: "center", justifyContent: "center", gap: 6, marginTop: spacing.lg, padding: 12, borderRadius: radius.md, borderWidth: 1, borderColor: colors.liturgical.red + "55" },
  archiveText: { fontFamily: fonts.uiSemi, fontSize: 13, color: colors.liturgical.red },
  previewWrap: { position: "relative", marginTop: 4 },
  previewImg: { width: "100%", height: 200, borderRadius: radius.md, backgroundColor: colors.background },
  previewClear: { position: "absolute", top: 8, right: 8, width: 26, height: 26, borderRadius: 13, backgroundColor: "rgba(0,0,0,0.55)", alignItems: "center", justifyContent: "center" },
  pickerBtn: { flexDirection: "row", alignItems: "center", gap: 8, paddingHorizontal: 14, paddingVertical: 10, borderRadius: radius.round, borderWidth: 1, borderColor: colors.borderSoft, backgroundColor: colors.background, alignSelf: "flex-start", marginTop: 6 },
  pickerBtnText: { fontFamily: fonts.uiSemi, fontSize: 12, color: colors.primary },
  center: { flex: 1, alignItems: "center", justifyContent: "center" },
  gateText: { fontFamily: fonts.bodyRegular, fontSize: 16, color: colors.textSecondary },
});
