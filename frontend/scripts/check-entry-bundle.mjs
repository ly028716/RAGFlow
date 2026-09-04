import { readdirSync, statSync } from 'node:fs'
import { join } from 'node:path'

const maxBytes = 500 * 1024
const assetsDirectory = join(import.meta.dirname, '..', 'dist', 'assets')
const entryBundle = readdirSync(assetsDirectory).find((file) => /^index-[\w-]+\.js$/.test(file))

if (!entryBundle) {
  throw new Error('Unable to find the built JavaScript entry bundle')
}

const entryBytes = statSync(join(assetsDirectory, entryBundle)).size

if (entryBytes > maxBytes) {
  throw new Error(
    `Entry bundle is ${(entryBytes / 1024).toFixed(1)} KiB; budget is ${maxBytes / 1024} KiB`,
  )
}

console.log(`Entry bundle is ${(entryBytes / 1024).toFixed(1)} KiB within the ${maxBytes / 1024} KiB budget`)
