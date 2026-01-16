import { makeWASocket, useMultiFileAuthState, DisconnectReason, downloadMediaMessage } from '@whiskeysockets/baileys'
import express from 'express'
import pino from 'pino'
import axios from 'axios'
import qrcode from 'qrcode-terminal'
import { exec } from 'child_process'
import fs from 'fs'
import { promisify } from 'util'

const writeFile = promisify(fs.writeFile);
const unlink = promisify(fs.unlink);
const execPromise = promisify(exec);
const app = express();
app.use(express.json({ limit: '50mb' }));
const PORT = process.env.PORT || 3000;
const WEBHOOK_URL = process.env.WEBHOOK_URL;
const SESSION_PATH = './sessions_auth'; 
let sock = null; 
async function connectToWhatsApp() {
    const { state, saveCreds } = await useMultiFileAuthState(SESSION_PATH)
    sock = makeWASocket({
        logger: pino({ level: 'silent' }),
        auth: state,
        browser: ['Ubuntu', 'Chrome', '20.0.04']
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
            if (!msg.message) continue;
            let payload = { event: 'message', data: msg, media: null };
            const msgType = Object.keys(msg.message)[0];
            if (msgType === 'audioMessage' || msgType === 'imageMessage') {
                try {
                    const buffer = await downloadMediaMessage(msg, 'buffer', { logger: pino({ level: 'silent' }) });
                    payload.media = { type: msgType, base64: buffer.toString('base64') };
                } catch (e) { console.log('Error descarga media'); }
            }
            if (WEBHOOK_URL) try { await axios.post(WEBHOOK_URL, payload) } catch (e) {}
        }
    })
}
connectToWhatsApp();
app.post('/message/text', async (req, res) => {
    const { to, text } = req.body;
    try {
        const id = to.includes('@') ? to : `${to}@s.whatsapp.net`;
        await sock.sendMessage(id, { text });
        res.json({ status: 'sent' });
    } catch (e) { res.status(500).send(e.message); }
})

app.post('/message/media', async (req, res) => {
    const { to, type, base64, caption } = req.body;
    try {
        const id = to.includes('@') ? to : `${to}@s.whatsapp.net`;
        let buffer = Buffer.from(base64, 'base64');
        if (type === 'audio') {
            const tIn = `in_${Date.now()}.mp3`, tOut = `out_${Date.now()}.opus`;
            await writeFile(tIn, buffer);
            // CONFIGURACIÓN BLINDADA: Mono, 48khz, bitrate bajo y formato OGG-OPUS estricto
            await execPromise(`ffmpeg -i ${tIn} -c:a libopus -ac 1 -ar 48000 -b:a 16k -application voip ${tOut}`);
            const finalBuffer = fs.readFileSync(tOut);
            await sock.sendMessage(id, { 
                audio: finalBuffer, 
                mimetype: 'audio/ogg; codecs=opus', 
                ptt: true 
            });
            await unlink(tIn); await unlink(tOut);
            console.log('✅ Audio enviado con éxito');
        } else {
            await sock.sendMessage(id, { image: buffer, caption: caption || '' });
        }
        res.json({ status: 'ok' });
    } catch (e) { console.error("Error:", e); res.status(500).send(e.message); }
})
app.listen(PORT, () => console.log(`Puerto ${PORT}`));
