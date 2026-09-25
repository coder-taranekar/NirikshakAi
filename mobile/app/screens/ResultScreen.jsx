/**
 * ResultScreen — placeholder for Task 12.
 * Displays compliance result after a scan.
 */

import React from "react";
import { View, Text, StyleSheet, TouchableOpacity } from "react-native";

export default function ResultScreen({ route, navigation }) {
  const { inspectionId } = route.params ?? {};

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Compliance Result</Text>
      <Text style={styles.id}>Inspection: {inspectionId ?? "—"}</Text>
      <Text style={styles.body}>
        Full result display coming in Task 12.{"\n\n"}
        Will include:{"\n"}
        • Compliance score ring{"\n"}
        • Per-declaration pass/fail cards{"\n"}
        • Annotated label image viewer{"\n"}
        • Download PDF report button{"\n"}
        • Penalty assessment
      </Text>
      <TouchableOpacity style={styles.back} onPress={() => navigation.navigate("Home")}>
        <Text style={styles.backText}>← Back to Home</Text>
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, justifyContent: "center", alignItems: "center",
               padding: 24, backgroundColor: "#f3f4f6" },
  title:     { fontSize: 22, fontWeight: "700", color: "#1d4ed8", marginBottom: 8 },
  id:        { fontSize: 13, color: "#6b7280", marginBottom: 16 },
  body:      { fontSize: 15, color: "#374151", lineHeight: 24, textAlign: "left" },
  back:      { marginTop: 32, padding: 12 },
  backText:  { color: "#1d4ed8", fontSize: 16, fontWeight: "600" },
});
