import { Redirect, useLocalSearchParams } from "expo-router";

/**
 * Backwards-compatible redirect: /rosary → /prayer/rosary so any older
 * deep-links continue to function. The Prayer hub is the canonical entry.
 */
export default function RosaryRedirect() {
  const params = useLocalSearchParams<{ date?: string; season?: string }>();
  const search: Record<string, string> = { kind: "rosary" };
  if (typeof params.date === "string") search.date = params.date;
  if (typeof params.season === "string") search.season = params.season;
  return <Redirect href={{ pathname: "/prayer/[kind]", params: search }} />;
}
