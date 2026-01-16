import { makeWASocket, useMultiFileAuthState, DisconnectReason } from '@whiskeysockets/baileys'
import express from 'express'
import pino from 'pino'
import axios from 'axios'
import qrcode from 'qrcode-terminal'

const app = express()
app.use(express.json())
const PORT = process.env.PORT || 3000
const WEBHOOK_URL = process.env.WEBHOOK_URL
const SESSION_PATH = './sessions_auth' 

// --- VARIABLE GLOBAL PARA MANTENER LA CONEXIÓN ACTIVA ---
let sock = null; 

async function connectToWhatsApp() {
    console.log('🔄 Conectando a WhatsApp...')
    const { state, saveCreds } = await useMultiFileAuthState(SESSION_PATH)

    // Asignamos a la variable global
    sock = makeWASocket({
        logger: pino({ level: 'silent' }),
        printQRInTerminal: true,
        auth: state,
        connectTimeoutMs: 60000,
        syncFullHistory: false,
        browser: ['Ubuntu', 'Chrome', '20.0.04']
    })
    sock.ev.on('connection.update', async (update) => {
        const { connection, lastDisconnect, qr } = update
        
        if (qr) {
            console.log('\n✨ QR RECIBIDO ✨')
            qrcode.generate(qr, { small: true })
        }

        if (connection === 'close') {
            const error = lastDisconnect?.error
            const statusCode = error?.output?.statusCode
            console.log('❌ CONEXIÓN CERRADA. Razón:', error?.message)
            
            // Si no es un log-out manual, reconectar automáticamente
            if (statusCode !== DisconnectReason.loggedOut) {
                setTimeout(connectToWhatsApp, 3000)
            }
        } else if (connection === 'open') {
            console.log('✅ ¡CONECTADO Y LISTO! 🚀')
        }
    })

    sock.ev.on('creds.update', saveCreds)

    sock.ev.on('messages.upsert', async ({ messages, type }) => {
        if (type !== 'notify') return
        for (const msg of messages) {
            if (!msg.message) continue
            if (WEBHOOK_URL) {
                try {
                    await axios.post(WEBHOOK_URL, { event: 'message', data: msg })
                } catch (e) { console.error('Error webhook:', e.message) }
            }
        }
    })
}
// Iniciamos la conexión por primera vez
connectToWhatsApp()

// --- API (FUERA DE LA FUNCIÓN DE CONEXIÓN) ---

app.get('/health', (req, res) => res.send('OK'))

app.post('/message/navros/text', async (req, res) => {
    const { to, text } = req.body
    
    // Verificamos si hay conexión activa
    if (!sock) {
        return res.status(503).json({ error: 'WhatsApp no está inicializado todavía' })
    }

    try {
        const id = to.includes('@') ? to : `${to}@s.whatsapp.net`
        // Usamos la variable global 'sock'
        await sock.sendMessage(id, { text })
        res.json({ status: 'sent' })
    } catch (e) {
        console.error('Error enviando:', e.message)
        res.status(500).json({ error: e.message })
    }
})

app.listen(PORT, () => console.log(`Servidor API listo en puerto ${PORT}`))
