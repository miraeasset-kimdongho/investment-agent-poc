import { useEffect, useState } from 'react'
import FingerprintJS from '@fingerprintjs/fingerprintjs'
import axios from 'axios'
import './App.css'

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const REACTIONS = [
  { key: 'like',  emoji: '👍', label: '좋아요' },
  { key: 'love',  emoji: '❤️', label: '사랑해요' },
  { key: 'wow',   emoji: '😮', label: '놀라워요' },
  { key: 'haha',  emoji: '😂', label: '웃겨요' },
  { key: 'sad',   emoji: '😢', label: '슬퍼요' },
  { key: 'angry', emoji: '😠', label: '화나요' },
]

export default function App() {
  const [userUid, setUserUid]   = useState(null)
  const [greeting, setGreeting] = useState(null)
  const [selected, setSelected] = useState(null)
  const [loading, setLoading]   = useState(true)
  const [reacting, setReacting] = useState(false)
  const [error, setError]       = useState(null)
  const [feedback, setFeedback] = useState(null)

  useEffect(() => {
    FingerprintJS.load()
      .then(fp => fp.get())
      .then(result => setUserUid(result.visitorId))
      .catch(() => {
        let uid = sessionStorage.getItem('boc_uid')
        if (!uid) { uid = crypto.randomUUID(); sessionStorage.setItem('boc_uid', uid) }
        setUserUid(uid)
      })
  }, [])

  useEffect(() => {
    if (!userUid) return
    setLoading(true)
    Promise.all([
      axios.get(`${API_BASE}/greeting`),
      axios.get(`${API_BASE}/reaction/${userUid}`),
    ])
      .then(([greetRes, reactionRes]) => {
        setGreeting(greetRes.data.message)
        if (reactionRes.data.reaction) setSelected(reactionRes.data.reaction)
      })
      .catch(() => setError('서버에 연결할 수 없습니다. 잠시 후 다시 시도해주세요.'))
      .finally(() => setLoading(false))
  }, [userUid])

  const handleReaction = async (reactionKey) => {
    if (reacting) return
    setReacting(true)
    setFeedback(null)
    try {
      await axios.post(`${API_BASE}/reaction/${userUid}`, { reaction: reactionKey })
      setSelected(reactionKey)
      setFeedback({ ok: true, msg: '✅ 반응이 저장되었습니다!' })
      setTimeout(() => setFeedback(null), 2500)
    } catch {
      setFeedback({ ok: false, msg: '저장 중 오류가 발생했습니다.' })
    } finally {
      setReacting(false)
    }
  }

  if (loading) return (
    <div className="card">
      <div className="spinner" />
      <p className="status-text">불러오는 중...</p>
    </div>
  )

  if (error) return (
    <div className="card">
      <p className="error-text">{error}</p>
    </div>
  )

  const shortUid = userUid ? userUid.slice(0, 8).toUpperCase() : '...'

  return (
    <div className="card">
      <div className="card-icon">🩳</div>

      <div className="greeting">
        <div className="greeting-line">
          <span className="uid-badge">{shortUid}</span>님<br />
          <span className="greeting-message">{greeting}!</span>
        </div>
        <p className="subtitle">오늘 기분이 어떠신가요?</p>
      </div>

      <hr className="divider" />

      <p className="reaction-section-label">반응 남기기</p>

      <div className="reaction-grid">
        {REACTIONS.map(({ key, emoji, label }) => (
          <button
            key={key}
            className={`reaction-btn ${selected === key ? 'selected' : ''}`}
            onClick={() => handleReaction(key)}
            disabled={reacting}
          >
            <span className="reaction-emoji">{emoji}</span>
            <span className="reaction-label">{label}</span>
          </button>
        ))}
      </div>

      {feedback && (
        <p className={`feedback ${feedback.ok ? 'feedback--ok' : 'feedback--error'}`}>
          {feedback.msg}
        </p>
      )}

      <p className="uid-footer">UID: {userUid}</p>
    </div>
  )
}
