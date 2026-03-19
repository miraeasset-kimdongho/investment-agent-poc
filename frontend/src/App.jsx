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

  // 1) Fingerprint 로드
  useEffect(() => {
    FingerprintJS.load()
      .then(fp => fp.get())
      .then(result => setUserUid(result.visitorId))
      .catch(() => {
        let uid = sessionStorage.getItem('boc_uid')
        if (!uid) {
          uid = crypto.randomUUID()
          sessionStorage.setItem('boc_uid', uid)
        }
        setUserUid(uid)
      })
  }, [])

  // 2) Fingerprint 확보 후 인사말 + 기존 반응 fetch
  useEffect(() => {
    if (!userUid) return
    setLoading(true)
    Promise.all([
      axios.get(`${API_BASE}/greeting`),
      axios.get(`${API_BASE}/reaction/${userUid}`),
    ])
      .then(([greetRes, reactionRes]) => {
        setGreeting(greetRes.data.message)
        if (reactionRes.data.reaction) {
          setSelected(reactionRes.data.reaction)
        }
      })
      .catch(err => {
        console.error(err)
        setError('서버에 연결할 수 없습니다. 잠시 후 다시 시도해주세요.')
      })
      .finally(() => setLoading(false))
  }, [userUid])

  // 3) 반응 버튼 클릭
  const handleReaction = async (reactionKey) => {
    if (reacting) return
    setReacting(true)
    setFeedback(null)
    try {
      await axios.post(`${API_BASE}/reaction/${userUid}`, { reaction: reactionKey })
      setSelected(reactionKey)
      setFeedback('반응이 저장되었습니다!')
      setTimeout(() => setFeedback(null), 2500)
    } catch (err) {
      console.error(err)
      setFeedback('저장 중 오류가 발생했습니다.')
    } finally {
      setReacting(false)
    }
  }

  if (loading) {
    return (
      <div className="card">
        <div className="spinner" />
        <p className="status-text">불러오는 중...</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="card">
        <p className="error-text">{error}</p>
      </div>
    )
  }

  const shortUid = userUid ? userUid.slice(0, 8).toUpperCase() : '...'

  return (
    <div className="card">
      <h1 className="greeting-title">
        <span className="uid-badge">{shortUid}</span>님&nbsp;
        <span className="greeting-message">{greeting}!</span>
      </h1>

      <p className="subtitle">오늘 기분이 어떠신가요?</p>

      <div className="reaction-grid">
        {REACTIONS.map(({ key, emoji, label }) => (
          <button
            key={key}
            className={`reaction-btn ${selected === key ? 'selected' : ''}`}
            onClick={() => handleReaction(key)}
            disabled={reacting}
            title={label}
          >
            <span className="reaction-emoji">{emoji}</span>
            <span className="reaction-label">{label}</span>
          </button>
        ))}
      </div>

      {feedback && (
        <p className={`feedback ${feedback.includes('오류') ? 'feedback--error' : 'feedback--ok'}`}>
          {feedback}
        </p>
      )}

      <p className="uid-footer">UID: {userUid}</p>
    </div>
  )
}
