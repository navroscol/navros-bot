import { makeWASocket, useMultiFileAuthState, downloadMediaMessage } from '@whiskeysockets/baileys'
import express from 'express'
import pino from 'pino'
import axios from 'axios'
import qrcode from 'qrcode-terminal'
import fs from 'fs'

const app = express();
app.use(express.json({ limit: '50mb' }));
const PORT = 3000;
const WEBHOOK_URL = process.env.WEBHOOK_URL;
const SESSION_PATH = './sessions_auth';

async function connectToWhatsApp() {
    const { state, saveCreds } = await useMultiFileAuthState(SESSION_PATH)
    const sock = makeWASocket({
        logger: pino({ level: 'silent' }),
        auth: state,
        printQRInTerminal: true
    })

    sock.ev.on('connection.update', (update) => {
        const { connection, qr } = update;
        if (qr) qrcode.generate(qr, { small: true });
        if (connection === 'open') console.log('✅ BOT CONECTADO Y LISTO');
    })

    sock.ev.on('creds.update', saveCreds);

    sock.ev.on('messages.upsert', async ({ messages, type }) => {
        if (type !== 'notify') return;
        for (const msg of messages) {
            if (!msg.message || msg.key.fromMe) continue;
            console.log('📩 Mensaje recibido de:', msg.key.remoteJid);
            
            let payload = { event: 'message', data: msg, media: null };
            const msgType = Object.keys(msg.message)[0];

            if (msgType === 'audioMessage') {
                console.log('🎤 Procesando audio...');
                const buffer = await downloadMediaMessage(msg, 'buffer', {});
                payload.media = { type: 'audio', base64: buffer.toString('base64') };
            }

            if (WEBHOOK_URL) {
                try {
                    console.log('➡️ Enviando a cerebro:', WEBHOOK_URL);
                    await axios.post(WEBHOOK_URL, payload);
                } catch (e) {
                    console.log('❌ Error enviando al cerebro:', e.message);
                }
            }
        }
    });
}
connectToWhatsApp();
app.listen(PORT, () => console.log(`🚀 Motor en puerto ${PORT}`));
