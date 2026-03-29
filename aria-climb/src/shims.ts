/**
 * Global polyfills — must be imported before any BLE or binary parsing code.
 * Buffer is not available in the React Native JS environment by default.
 */
import { Buffer } from 'buffer';

// @ts-ignore
global.Buffer = global.Buffer ?? Buffer;
