import React, { useEffect, useState } from 'react';
import {
  View,
  Text,
  FlatList,
  TouchableOpacity,
  StyleSheet,
  Modal,
  TextInput,
  ActivityIndicator,
} from 'react-native';
import { useTranslation } from 'react-i18next';
import { useNavigation } from '@react-navigation/native';
import type { DrawerNavigationProp } from '@react-navigation/drawer';
import type { GymDrawerParamList } from '../../types/navigation';
import { useAuthStore } from '../../store/authStore';
import {
  scanForARIADevices,
  provisionDevice,
  type ARIAAdvertisedDevice,
  type ProvisioningStatus,
} from '../../services/ble/bleProvisioning';
import { waitForDeviceOnline } from '../../services/firebase/bleProvisioningVerifier';

type Nav = DrawerNavigationProp<GymDrawerParamList, 'Provisioning'>;

export function ProvisioningScreen() {
  const { t } = useTranslation();
  const navigation = useNavigation<Nav>();
  const user = useAuthStore((s) => s.user);
  const gymId = user?.homeGymId || 'default-gym';

  const [devices, setDevices] = useState<ARIAAdvertisedDevice[]>([]);
  const [scanning, setScanning] = useState(false);
  const [error, setError] = useState('');
  const [selected, setSelected] = useState<ARIAAdvertisedDevice | null>(null);

  const [wifiModalVisible, setWifiModalVisible] = useState(false);
  const [ssid, setSsid] = useState('');
  const [password, setPassword] = useState('');
  const [status, setStatus] = useState<ProvisioningStatus>('IDLE');
  const [statusMessage, setStatusMessage] = useState('');
  const [verifying, setVerifying] = useState(false);

  useEffect(() => {
    return () => {
      setScanning(false);
    };
  }, []);

  function handleScan() {
    setDevices([]);
    setError('');
    setScanning(true);
    const stop = scanForARIADevices(
      (dev) => {
        setDevices((prev) => {
          if (prev.find((d) => d.bleDevice.id === dev.bleDevice.id)) return prev;
          return [...prev, dev].sort((a, b) => (b.rssi ?? 0) - (a.rssi ?? 0));
        });
      },
      (err) => {
        setError(err.message);
        setScanning(false);
      }
    );
    setTimeout(() => {
      stop();
      setScanning(false);
    }, 15000);
  }

  function openProvisionModal(device: ARIAAdvertisedDevice) {
    setSelected(device);
    setSsid('');
    setPassword('');
    setStatus('IDLE');
    setStatusMessage('');
    setWifiModalVisible(true);
  }

  async function handleProvision() {
    if (!selected) return;
    setError('');
    if (!ssid.trim() || !password.trim()) {
      setError('Enter SSID and password.');
      return;
    }
    setStatus('SCANNING');
    setStatusMessage('Connecting to device…');

    const ok = await provisionDevice(
      selected,
      { ssid: ssid.trim(), password: password.trim(), gymId, deviceId: selected.deviceId },
      (s) => {
        setStatus(s);
        switch (s) {
          case 'CONNECTING':
            setStatusMessage('Connecting to ARIA device…');
            break;
          case 'SENDING_WIFI':
            setStatusMessage('Sending WiFi credentials…');
            break;
          case 'SENDING_GYM':
            setStatusMessage('Sending gym + device config…');
            break;
          case 'WAITING_REBOOT':
            setStatusMessage('Waiting for ESP32 to reboot…');
            break;
          default:
            break;
        }
      }
    );

    if (!ok) {
      setStatus('FAILED');
      setStatusMessage('Provisioning failed. Check power and try again.');
      return;
    }

    setStatus('WAITING_REBOOT');
    setStatusMessage('Device rebooting and connecting to WiFi…');
    setVerifying(true);
    const stopVerify = waitForDeviceOnline(
      gymId,
      selected.deviceId,
      () => {
        setVerifying(false);
        setStatus('SUCCESS');
        setStatusMessage('Device is online and reporting to Firebase.');
        setWifiModalVisible(false);
        // Navigate to DeviceDetail for this new device
        navigation.navigate('DeviceDetail', { deviceId: selected.deviceId });
        stopVerify();
      },
      () => {
        setVerifying(false);
        setStatus('FAILED');
        setStatusMessage('Device did not come online in time. Verify WiFi + gym config.');
        stopVerify();
      }
    );
  }

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Provision new ARIA devices</Text>
      <Text style={styles.subtitle}>
        Scan for nearby unprovisioned ARIA units, send WiFi + gym config, then verify they come
        online in Firebase.
      </Text>

      {error ? <Text style={styles.error}>{error}</Text> : null}

      <TouchableOpacity
        style={[styles.button, scanning && styles.buttonDisabled]}
        onPress={handleScan}
        disabled={scanning}
      >
        <Text style={styles.buttonText}>{scanning ? 'Scanning…' : 'Scan for devices'}</Text>
      </TouchableOpacity>

      <FlatList
        data={devices}
        keyExtractor={(item) => item.bleDevice.id}
        style={styles.list}
        renderItem={({ item }) => (
          <TouchableOpacity
            style={styles.deviceRow}
            onPress={() => openProvisionModal(item)}
          >
            <View>
              <Text style={styles.deviceName}>{item.deviceId}</Text>
              <Text style={styles.deviceDetail}>BLE: {item.bleDevice.name}</Text>
            </View>
            <Text style={styles.deviceRssi}>{item.rssi} dBm</Text>
          </TouchableOpacity>
        )}
        ListEmptyComponent={
          !scanning ? (
            <Text style={styles.empty}>
              No ARIA devices found yet. Tap "Scan for devices" to search over BLE.
            </Text>
          ) : null
        }
      />

      <Modal visible={wifiModalVisible} transparent animationType="slide">
        <View style={styles.modalBackdrop}>
          <View style={styles.modal}>
            <Text style={styles.modalTitle}>Provision {selected?.deviceId}</Text>
            <TextInput
              style={styles.input}
              placeholder="WiFi SSID"
              value={ssid}
              onChangeText={setSsid}
              autoCapitalize="none"
            />
            <TextInput
              style={styles.input}
              placeholder="WiFi password"
              value={password}
              onChangeText={setPassword}
              autoCapitalize="none"
              secureTextEntry
            />
            <Text style={styles.modalSubtitle}>Gym ID: {gymId}</Text>
            {statusMessage ? <Text style={styles.status}>{statusMessage}</Text> : null}
            {verifying && <ActivityIndicator style={{ marginTop: 8 }} />}

            <View style={styles.modalButtons}>
              <TouchableOpacity
                style={[styles.button, styles.modalButton]}
                onPress={handleProvision}
                disabled={status === 'SENDING_WIFI' || status === 'SENDING_GYM' || verifying}
              >
                <Text style={styles.buttonText}>
                  {status === 'IDLE' || status === 'SCANNING' ? 'Start provisioning' : 'Retry'}
                </Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={[styles.button, styles.modalButton, styles.cancelButton]}
                onPress={() => setWifiModalVisible(false)}
              >
                <Text style={styles.buttonText}>Cancel</Text>
              </TouchableOpacity>
            </View>
          </View>
        </View>
      </Modal>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: 24 },
  title: { fontSize: 22, marginBottom: 4 },
  subtitle: { color: '#666', marginBottom: 12 },
  error: { color: 'red', marginBottom: 8 },
  button: {
    backgroundColor: '#1a1a2e',
    padding: 12,
    borderRadius: 8,
    alignItems: 'center',
    marginBottom: 12,
  },
  buttonDisabled: { opacity: 0.6 },
  buttonText: { color: '#fff', fontSize: 16 },
  list: { flex: 1 },
  deviceRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 12,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderColor: '#ddd',
  },
  deviceName: { fontSize: 16 },
  deviceDetail: { fontSize: 12, color: '#666' },
  deviceRssi: { fontSize: 12, color: '#333' },
  empty: { marginTop: 16, color: '#666' },
  modalBackdrop: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.4)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  modal: {
    width: '90%',
    backgroundColor: '#fff',
    padding: 16,
    borderRadius: 12,
  },
  modalTitle: { fontSize: 18, marginBottom: 8 },
  modalSubtitle: { color: '#666', marginBottom: 8 },
  input: {
    borderWidth: 1,
    borderColor: '#ccc',
    borderRadius: 8,
    padding: 10,
    marginBottom: 8,
  },
  status: { fontSize: 13, color: '#333', marginTop: 4 },
  modalButtons: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginTop: 12,
  },
  modalButton: { flex: 1, marginHorizontal: 4 },
  cancelButton: { backgroundColor: '#6b7280' },
});

