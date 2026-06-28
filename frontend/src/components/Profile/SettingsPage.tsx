import { useState } from 'react'
import { motion } from 'framer-motion'
import { Settings2, Palette, Volume2, Monitor } from 'lucide-react'
import toast from 'react-hot-toast'
import clsx from 'clsx'
import { useAuthStore } from '../../store/authStore'
import { usersApi } from '../../api/client'

const BOARD_THEMES = ['cosmic', 'classic', 'midnight', 'emerald']

export default function SettingsPage() {
  const { user, updateUser } = useAuthStore()
  const [saving, setSaving] = useState(false)
  const [form, setForm] = useState({
    bio: user?.bio ?? '',
    board_theme: user?.board_theme ?? 'cosmic',
    show_coordinates: user?.show_coordinates ?? true,
    auto_promote_queen: user?.auto_promote_queen ?? true,
    sound_enabled: user?.sound_enabled ?? true,
  })

  const handleSave = async () => {
    setSaving(true)
    try {
      const { data } = await usersApi.updateMe(form)
      updateUser(data)
      toast.success('Settings saved!')
    } catch {
      toast.error('Failed to save settings')
    } finally {
      setSaving(false)
    }
  }

  const Toggle = ({ label, key: k, description }: { label: string; key: keyof typeof form; description?: string }) => (
    <div className="flex items-center justify-between py-3 border-b border-nebula-700/30 last:border-0">
      <div>
        <p className="text-sm font-medium text-nebula-200">{label}</p>
        {description && <p className="text-xs text-nebula-400 mt-0.5">{description}</p>}
      </div>
      <button
        onClick={() => setForm(f => ({ ...f, [k]: !f[k as keyof typeof form] }))}
        className={clsx(
          'w-11 h-6 rounded-full transition-all duration-200 relative',
          form[k as keyof typeof form] ? 'bg-nebula-500' : 'bg-nebula-700'
        )}
      >
        <span className={clsx(
          'absolute top-0.5 w-5 h-5 bg-white rounded-full shadow transition-all duration-200',
          form[k as keyof typeof form] ? 'left-5' : 'left-0.5'
        )} />
      </button>
    </div>
  )

  return (
    <div className="container mx-auto px-4 py-10 max-w-2xl">
      <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }}>
        <div className="flex items-center gap-3 mb-8">
          <Settings2 size={26} className="text-nebula-400" />
          <h1 className="text-2xl font-display font-bold text-nebula-100">Settings</h1>
        </div>

        {/* Profile */}
        <div className="card mb-4">
          <h2 className="font-semibold text-nebula-200 mb-4 flex items-center gap-2">
            <Monitor size={16} className="text-nebula-400" /> Profile
          </h2>
          <div>
            <label className="text-sm text-nebula-300 font-medium mb-1.5 block">Bio</label>
            <textarea
              className="input resize-none h-20"
              placeholder="Tell people about yourself…"
              value={form.bio}
              onChange={e => setForm(f => ({ ...f, bio: e.target.value.slice(0, 200) }))}
            />
            <p className="text-xs text-nebula-500 text-right mt-1">{form.bio.length}/200</p>
          </div>
        </div>

        {/* Board */}
        <div className="card mb-4">
          <h2 className="font-semibold text-nebula-200 mb-4 flex items-center gap-2">
            <Palette size={16} className="text-nebula-400" /> Board Theme
          </h2>
          <div className="grid grid-cols-4 gap-2 mb-4">
            {BOARD_THEMES.map(t => (
              <button key={t} onClick={() => setForm(f => ({ ...f, board_theme: t }))}
                className={clsx(
                  'py-2 rounded-xl text-sm capitalize font-medium transition-all',
                  form.board_theme === t
                    ? 'bg-nebula-500 text-white shadow-nebula'
                    : 'bg-nebula-800/60 text-nebula-400 hover:bg-nebula-700/60'
                )}>
                {t}
              </button>
            ))}
          </div>
          <Toggle label="Show Coordinates" key="show_coordinates" description="Display file and rank labels on the board" />
          <Toggle label="Auto-promote to Queen" key="auto_promote_queen" description="Automatically promote pawns to queen" />
        </div>

        {/* Audio */}
        <div className="card mb-6">
          <h2 className="font-semibold text-nebula-200 mb-4 flex items-center gap-2">
            <Volume2 size={16} className="text-nebula-400" /> Audio
          </h2>
          <Toggle label="Sound Effects" key="sound_enabled" description="Play sounds on moves, captures, and game events" />
        </div>

        <button onClick={handleSave} disabled={saving} className="btn-primary w-full justify-center py-3.5 disabled:opacity-50">
          {saving ? 'Saving…' : 'Save Settings'}
        </button>
      </motion.div>
    </div>
  )
}
