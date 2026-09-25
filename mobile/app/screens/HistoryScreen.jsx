/**
 * HistoryScreen — placeholder for Task 12.
 * Lists past inspections for the logged-in inspector.
 */

import React from "react";
import { View, Text, StyleSheet, TouchableOpacity } from "react-native";

export default function HistoryScreen({ navigation }) {
  return (
    <View style={styles.container}>
      <Text style={styles.title}>Inspection History</Text>
      <Text style={styles.body}>
        Full history list coming in Task 12.{"\n\n"}
        Will include:{"\n"}
        • Paginated inspection list{"\n"}
        • Status badges (Compliant / Non-Compliant){"\n"}
        • Search by product name{"\n"}
        • Tap to view full result{"\n"}
        • Offline queued items
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
