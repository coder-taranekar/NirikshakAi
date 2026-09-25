/**
 * HomeScreen — field inspector's main hub.
 * Placeholder for full implementation in Task 12.
 * Core navigation and offline queue badge wired already.
 */

import React, { useEffect, useState } from "react";
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  SafeAreaView,
  Alert,
} from "react-native";
import * as SecureStore from "expo-secure-store";
import { getQueueLength } from "../services/offlineQueue";

export default function HomeScreen({ navigation }) {
  const [user, setUser]           = useState(null);
  const [queueCount, setQueueCount] = useState(0);

  useEffect(() => {
    (async () => {
      const raw = await SecureStore.getItemAsync("user");
      if (raw) setUser(JSON.parse(raw));
      const count = await getQueueLength();
      setQueueCount(count);
    })();
  }, []);

  const handleLogout = async () => {
    Alert.alert("Sign Out", "Are you sure you want to sign out?", [
      { text: "Cancel", style: "cancel" },
      {
        text: "Sign Out",
        style: "destructive",
        onPress: async () => {
          await SecureStore.deleteItemAsync("access_token");
          await SecureStore.deleteItemAsync("refresh_token");
          await SecureStore.deleteItemAsync("user");
          navigation.replace("Login");
        },
      },
    ]);
  };

  return (
    <SafeAreaView style={styles.container}>
      {/* Header */}
      <View style={styles.header}>
        <View>
          <Text style={styles.greeting}>
            Hello, {user?.name?.split(" ")[0] ?? "Inspector"}
          </Text>
          <Text style={styles.subGreeting}>
            {user?.state ? `${user.state} · ` : ""}Field Inspection
          </Text>
        </View>
        <TouchableOpacity onPress={handleLogout}>
          <Text style={styles.logoutText}>Sign Out</Text>
        </TouchableOpacity>
      </View>

      {/* Offline queue badge */}
      {queueCount > 0 && (
        <View style={styles.queueBanner}>
          <Text style={styles.queueText}>
            ⏳ {queueCount} scan{queueCount > 1 ? "s" : ""} pending sync
          </Text>
        </View>
      )}

      {/* Action cards */}
      <View style={styles.actions}>
        <TouchableOpacity
          style={[styles.actionCard, styles.primaryCard]}
          onPress={() => navigation.navigate("CameraScan")}
        >
          <Text style={styles.actionIcon}>📷</Text>
          <Text style={styles.actionTitle}>Scan Label</Text>
          <Text style={styles.actionDesc}>Use camera to scan a product label</Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={[styles.actionCard, styles.secondaryCard]}
          onPress={() => navigation.navigate("CameraScan", { mode: "gallery" })}
        >
          <Text style={styles.actionIcon}>🖼️</Text>
          <Text style={styles.actionTitle}>Upload Image</Text>
          <Text style={styles.actionDesc}>Choose from photo gallery</Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={[styles.actionCard, styles.secondaryCard]}
          onPress={() => navigation.navigate("History")}
        >
          <Text style={styles.actionIcon}>📋</Text>
          <Text style={styles.actionTitle}>Inspection History</Text>
          <Text style={styles.actionDesc}>View past compliance checks</Text>
        </TouchableOpacity>
      </View>

      <Text style={styles.version}>LabelGuard v1.0 · Full implementation in Task 12</Text>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container:    { flex: 1, backgroundColor: "#f3f4f6" },
  header:       { flexDirection: "row", justifyContent: "space-between",
                  alignItems: "center", padding: 20, backgroundColor: "#1d4ed8" },
  greeting:     { fontSize: 20, fontWeight: "700", color: "#fff" },
  subGreeting:  { fontSize: 13, color: "#bfdbfe", marginTop: 2 },
  logoutText:   { color: "#bfdbfe", fontSize: 14 },
  queueBanner:  { backgroundColor: "#fef3c7", padding: 10,
                  alignItems: "center", borderBottomWidth: 1, borderBottomColor: "#fde68a" },
  queueText:    { fontSize: 13, color: "#92400e", fontWeight: "600" },
  actions:      { padding: 20, gap: 12 },
  actionCard:   { borderRadius: 12, padding: 20, flexDirection: "row",
                  alignItems: "center", gap: 14 },
  primaryCard:  { backgroundColor: "#1d4ed8" },
  secondaryCard:{ backgroundColor: "#fff", borderWidth: 1, borderColor: "#e5e7eb" },
  actionIcon:   { fontSize: 28 },
  actionTitle:  { fontSize: 16, fontWeight: "700", color: "#fff", flex: 1 },
  actionDesc:   { fontSize: 13, color: "#bfdbfe" },
  version:      { textAlign: "center", color: "#9ca3af", fontSize: 11, marginTop: "auto", padding: 16 },
});
