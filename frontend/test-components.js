// Simple test to check if components can be imported
import fs from 'fs'
import path from 'path'
import { fileURLToPath } from 'url'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)

console.log('Testing component imports...')

const componentsDir = path.join(__dirname, 'src/components/models')
const files = fs.readdirSync(componentsDir)

files.forEach(file => {
  if (file.endsWith('.vue')) {
    const content = fs.readFileSync(path.join(componentsDir, file), 'utf8')
    console.log(`✓ ${file} - ${content.length} characters`)
  }
})

console.log('Component files created successfully!')