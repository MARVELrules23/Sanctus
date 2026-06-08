import { Redirect } from "expo-router";

import { useAuth } from "@/src/auth-context";

export default function Index() {
  const { user, loading } = useAuth();
  if (loading) return null;
  return <Redirect href={user ? "/(tabs)" : "/login"} />;
}
