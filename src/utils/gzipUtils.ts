import { gzipSync, gunzipSync } from 'zlib';
import fs from 'fs';

export function gzipWrite(filePath: string, content: string): Promise<void> {
  return new Promise((resolve, reject) => {
    const compressed = gzipSync(content, { level: 6 });
    fs.writeFile(filePath, compressed, (err) => {
      if (err) reject(err);
      else resolve();
    });
  });
}

export async function gzipReadToStream(gzipPath: string, outputStream: fs.WriteStream): Promise<void> {
  const compressed = await fs.promises.readFile(gzipPath);
  const decompressed = gunzipSync(compressed);
  outputStream.write(decompressed);
  outputStream.end();
}

export async function gzipReadToString(gzipPath: string): Promise<string> {
  const compressed = await fs.promises.readFile(gzipPath);
  const decompressed = gunzipSync(compressed);
  return decompressed.toString('utf-8');
}

export function isGzipPath(filePath: string): boolean {
  return filePath.endsWith('.gz');
}

export function toGzipPath(filePath: string): string {
  return filePath + '.gz';
}

export function fromGzipPath(gzipPath: string): string {
  if (gzipPath.endsWith('.gz')) {
    return gzipPath.slice(0, -3);
  }
  return gzipPath;
}
