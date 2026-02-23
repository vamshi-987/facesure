// Utility for image compression using browser-image-compression
import imageCompression from 'browser-image-compression';

export async function compressImage(file, options = { maxSizeMB: 1, maxWidthOrHeight: 1024 }) {
  try {
    const compressedFile = await imageCompression(file, options);
    return compressedFile;
  } catch (error) {
    console.error('Image compression error:', error);
    throw error;
  }
}
