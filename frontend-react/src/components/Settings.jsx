import React, { useState, useEffect, useRef } from 'react';
import { 
  Wifi, WifiOff, Plus, Trash2, HelpCircle, Smartphone, Terminal, QrCode
} from 'lucide-react';
import { 
  fetchChannels, fetchCreateChannel, fetchChannelQR, fetchChannelStatus, fetchDeleteChannel 
} from '../api';

const mockLogs = [
  { time: '2026-07-17 23:45:12', type: 'WARNING', msg: 'Maya prompt parsing fallback regex triggered' },
  { time: '2026-07-17 23:44:33', type: 'ERROR', msg: 'Failed to push metadata to Google Drive (NetworkTimeout)' },
  { time: '2026-07-17 23:40:01', type: 'INFO', msg: 'System initialized successfully. Uvicorn started on port 8080' },
];

export default function Settings({ t }) {
  const [channels, setChannels] = useState([]);
  const [phone, setPhone] = useState('');
  const [qrCode, setQrCode] = useState(null);
  const [qrStatus, setQrStatus] = useState('');
  const [connecting, setConnecting] = useState(false);

  const qrIntervalRef = useRef(null);

  useEffect(() => {
    loadChannels();
    return () => {
      if (qrIntervalRef.current) {
        clearInterval(qrIntervalRef.current);
      }
    };
  }, []);

  async function loadChannels() {
    try {
      const data = await fetchChannels() || [];
      setChannels(data);
    } catch (e) {
      console.error(e);
    }
  }

  async function handleConnect() {
    if (!phone.trim()) return;
    setConnecting(true);
    setQrCode(null);
    setQrStatus('Sedang memulakan sesi...');
    try {
      const ch = await fetchCreateChannel(phone);
      if (ch && ch.id) {
        pollQR(ch.id);
      }
    } catch (e) {
      setQrStatus('Gagal membuat saluran.');
      console.error(e);
    } finally {
      setConnecting(false);
    }
  }

  async function pollQR(channelId) {
    setQrCode(null);
    setQrStatus('Sedang menjana kod QR...');
    
    if (qrIntervalRef.current) clearInterval(qrIntervalRef.current);
    
    qrIntervalRef.current = setInterval(async () => {
      try {
        const qrRes = await fetchChannelQR(channelId);
        if (qrRes) {
          if (qrRes.status === 'connected') {
            clearInterval(qrIntervalRef.current);
            qrIntervalRef.current = null;
            setQrCode(null);
            setQrStatus('WhatsApp berjaya disambungkan!');
            loadChannels();
          } else if (qrRes.qr) {
            setQrCode(qrRes.qr);
            setQrStatus('Scan kod QR di bawah (kod dikemaskini secara automatik):');
          } else {
            setQrStatus('Menunggu kod QR dijana...');
          }
        }
      } catch (e) {
        console.error(e);
      }
    }, 5000);
  }

  async function handleDisconnect(id) {
    if (!confirm('Adakah anda pasti mahu memutuskan sambungan nombor ini?')) return;
    try {
      await fetchDeleteChannel(id);
      loadChannels();
    } catch (e) {
      console.error(e);
    }
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      {/* Left Columns - WhatsApp Configuration */}
      <div className="lg:col-span-2 space-y-6">
        {/* Connection panel */}
        <div className="glass-card p-5 space-y-4">
          <div>
            <h3 className="text-base font-semibold">{t('wa-connection-title')}</h3>
            <p className="text-xs text-text-muted">Sambung dan urus nombor WhatsApp Business anda dengan AI Engine.</p>
          </div>

          <div className="flex space-x-2">
            <input 
              type="text" 
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              placeholder="+60123456789"
              className="input-field max-w-xs"
            />
            <button 
              onClick={handleConnect}
              disabled={connecting || !phone.trim()}
              className="btn-primary"
            >
              <Plus className="w-4 h-4 mr-1.5" />
              {connecting ? 'Menyambung...' : t('wa-connect-btn')}
            </button>
          </div>

          {qrStatus && (
            <div className="p-4 bg-surface-raised border border-border rounded-lg flex flex-col items-center space-y-3">
              <span className="text-xs font-semibold text-primary">{qrStatus}</span>
              {qrCode && (
                <div className="bg-white p-2 rounded-lg">
                  <img 
                    src={qrCode.startsWith('data:') ? qrCode : `data:image/png;base64,${qrCode}`} 
                    alt="Scan QR code" 
                    className="w-48 h-48"
                  />
                </div>
              )}
            </div>
          )}

          <div className="space-y-3 pt-2">
            <h4 className="text-xs font-bold text-text-muted uppercase tracking-wider">
              Nombor Disambungkan
            </h4>
            <div className="space-y-2">
              {channels.length > 0 ? (
                channels.map((ch) => {
                  const statusMeta = {
                    connected: { icon: Wifi, color: 'text-accent-success', label: 'Connected & Active' },
                    pending_qr: { icon: HelpCircle, color: 'text-accent-gold', label: 'Menunggu imbasan QR' },
                    disconnected: { icon: WifiOff, color: 'text-accent-danger', label: 'Terputus' },
                  }[ch.status] || { icon: WifiOff, color: 'text-text-muted', label: ch.status || 'Unknown' };
                  const StatusIcon = statusMeta.icon;
                  return (
                    <div key={ch.id} className="flex items-center justify-between p-3 rounded bg-surface-raised border border-border">
                      <div className="flex items-center space-x-3">
                        <Smartphone className="w-4 h-4 text-text-muted" />
                        <div className="text-xs">
                          <p className="font-semibold">{ch.phone_number}</p>
                          <span className={`text-[10px] font-medium flex items-center mt-0.5 ${statusMeta.color}`}>
                            <StatusIcon className="w-3 h-3 mr-0.5" /> {statusMeta.label}
                          </span>
                        </div>
                      </div>
                      <div className="flex items-center space-x-2">
                        {ch.status === 'pending_qr' && (
                          <button
                            onClick={() => pollQR(ch.id)}
                            className="bg-primary/10 hover:bg-primary/20 text-primary py-1 px-2.5 text-[10px] font-semibold flex items-center rounded transition-all"
                          >
                            <QrCode className="w-3.5 h-3.5 mr-1" /> Tunjukkan QR
                          </button>
                        )}
                        <button
                          onClick={() => handleDisconnect(ch.id)}
                          className="text-text-muted hover:text-accent-danger p-2 rounded hover:bg-surface-raised transition-all"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </div>
                  );
                })
              ) : (
                <div className="p-4 text-center text-xs text-text-muted bg-surface rounded">
                  {t('wa-no-channels')}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Right Column - Error & Log Monitor */}
      <div className="glass-card p-5 space-y-4 h-fit">
        <div className="flex items-center justify-between border-b border-border pb-3">
          <div>
            <h3 className="text-base font-semibold">Log Ralat & Sistem</h3>
            <p className="text-xs text-text-muted">Aktiviti diagnostik pelayan masa nyata.</p>
          </div>
          <Terminal className="w-4 h-4 text-primary" />
        </div>

        <div className="space-y-3">
          {mockLogs.map((log, idx) => (
            <div key={idx} className="p-3 bg-surface-raised border border-border rounded text-xs space-y-1">
              <div className="flex items-center justify-between">
                <span className={`px-2 py-0.5 rounded font-mono text-[9px] font-semibold ${
                  log.type === 'ERROR' 
                    ? 'bg-accent-danger/10 text-accent-danger' 
                    : log.type === 'WARNING' 
                      ? 'bg-accent-gold/10 text-accent-gold' 
                      : 'bg-accent-success/10 text-accent-success'
                }`}>
                  {log.type}
                </span>
                <span className="text-[9px] text-text-faint font-mono">{log.time}</span>
              </div>
              <p className="font-mono text-[11px] text-text-muted leading-relaxed">
                {log.msg}
              </p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}