/**
 * Offline Queue Service
 *
 * When the device has no internet connection, scans are queued locally
 * in AsyncStorage and synced automatically when connectivity returns.
 *
 * Queue item shape:
 * {
 *   id: string (uuid),
 *   imageUri: string (local file path),
 *   productId: string | null,
 *   state: string | null,
 *   source: "camera" | "upload",
 *   queuedAt: ISO string
 * }
 */

import AsyncStorage from "@react-native-async-storage/async-storage";
import NetInfo from "@react-native-community/netinfo";
import * as FileSystem from "expo-file-system";
import apiClient from "./api";

const QUEUE_KEY = "labelguard_offline_queue";

// ── Read / Write helpers ──────────────────────────────────────────

async function readQueue() {
  try {
    const raw = await AsyncStorage.getItem(QUEUE_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

async function writeQueue(queue) {
  await AsyncStorage.setItem(QUEUE_KEY, JSON.stringify(queue));
}

// ── Public API ────────────────────────────────────────────────────

/**
 * Add a scan to the offline queue.
 * Called when a scan is attempted with no connectivity.
 */
export async function enqueueOfflineScan(item) {
  const queue = await readQueue();
  const entry = {
    id: `offline_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
    ...item,
    queuedAt: new Date().toISOString(),
  };
  queue.push(entry);
  await writeQueue(queue);
  return entry.id;
}

/**
 * Returns the current number of items in the offline queue.
 */
export async function getQueueLength() {
  const queue = await readQueue();
  return queue.length;
}

/**
 * Returns the full offline queue for display in the UI.
 */
export async function getPendingScans() {
  return readQueue();
}

/**
 * Attempt to sync all queued scans to the server.
 * Should be called when connectivity is detected.
 * Returns { synced: number, failed: number }
 */
export async function syncOfflineQueue(onProgress) {
  const queue = await readQueue();
  if (queue.length === 0) return { synced: 0, failed: 0 };

  const netState = await NetInfo.fetch();
  if (!netState.isConnected) return { synced: 0, failed: 0 };

  let synced = 0;
  let failed = 0;
  const remaining = [];

  for (const item of queue) {
    try {
      // Read the image file from local storage
      const imageInfo = await FileSystem.getInfoAsync(item.imageUri);
      if (!imageInfo.exists) {
        // File gone — drop from queue silently
        continue;
      }

      // Build multipart form data
      const formData = new FormData();
      formData.append("file", {
        uri: item.imageUri,
        name: "label.jpg",
        type: "image/jpeg",
      });
      if (item.productId) formData.append("product_id", item.productId);
      if (item.state) formData.append("state", item.state);
      formData.append("source", item.source ?? "camera");

      await apiClient.post("/inspections", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });

      synced++;
      if (onProgress) onProgress({ synced, total: queue.length, item });
    } catch {
      failed++;
      remaining.push(item);  // Keep failed items for retry
    }
  }

  await writeQueue(remaining);
  return { synced, failed };
}

/**
 * Clear the entire offline queue (e.g. on logout).
 */
export async function clearQueue() {
  await AsyncStorage.removeItem(QUEUE_KEY);
}
