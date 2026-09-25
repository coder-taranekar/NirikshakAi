/**
 * CameraScanScreen — placeholder for Task 12.
 * Navigation entry point wired; full camera + OCR flow implemented in Task 12.
 */

import React from "react";
import { View, Text, StyleSheet, TouchableOpacity } from "react-native";

export default function CameraScanScreen({ navigation }) {
  return (
    <View style={styles.container}>
      <Text style={styles.title}>Camera Scan</Text>
      <Text style={styles.body}>
        Full camera scan implementation coming in Task 12.{"\n\n"}
        Will include:{"\n"}
        • Live camera viewfinder{"\n"}
        • One-tap capture{"\n"}
        • Instant compliance result{"\n"}
        • Offline queue if no network
      </Text>
      <TouchableOpacity style={styles.back} onPress={() => navigation.goBack()}>
        <Text style={styles.backText}>← Back</Text>
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, justifyContent: "center", alignItems: "center",
               padding: 24, backgroundColor: "#f3f4f6" },
  title:     { fontSize: 22, fontWeight: "700", color: "#1d4ed8", marginBottom: 16 },
  body:      { fontSize: 15, color: "#374151", lineHeight: 24, textAlign: "left" },
  back:      { marginTop: 32, padding: 12 },
  backText:  { color: "#1d4ed8", fontSize: 16, fontWeight: "600" },
});
