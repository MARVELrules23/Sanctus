import React from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";
import { colors, fonts, radius, spacing } from "@/src/theme";

type Props = { children: React.ReactNode };
type State = { hasError: boolean };

/**
 * App-wide error boundary. Catches render-time errors anywhere in the tree
 * and shows a calm recovery screen instead of a blank white crash — a
 * stability safeguard reviewers (Apple 2.1) look for.
 */
export default class ErrorBoundary extends React.Component<Props, State> {
  state: State = { hasError: false };

  static getDerivedStateFromError(): State {
    return { hasError: true };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    console.error("Uncaught render error:", error, info?.componentStack);
  }

  reset = () => this.setState({ hasError: false });

  render() {
    if (this.state.hasError) {
      return (
        <View style={styles.container} testID="app-error-boundary">
          <Text style={styles.title}>Something went wrong</Text>
          <Text style={styles.body}>
            We hit an unexpected error. Please try again — your saved data is safe.
          </Text>
          <Pressable onPress={this.reset} style={styles.button} testID="error-boundary-retry">
            <Text style={styles.buttonText}>Try again</Text>
          </Pressable>
        </View>
      );
    }
    return this.props.children;
  }
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    padding: spacing.xl,
    backgroundColor: colors.background,
  },
  title: { fontFamily: fonts.headingSemi, fontSize: 22, color: colors.textPrimary, marginBottom: spacing.sm, textAlign: "center" },
  body: { fontFamily: fonts.bodyRegular, fontSize: 15, color: colors.textSecondary, textAlign: "center", lineHeight: 22, marginBottom: spacing.lg },
  button: { backgroundColor: colors.primary, paddingVertical: 13, paddingHorizontal: spacing.xl, borderRadius: radius.md },
  buttonText: { fontFamily: fonts.uiSemi, color: "#FFFFFF", fontSize: 15 },
});
