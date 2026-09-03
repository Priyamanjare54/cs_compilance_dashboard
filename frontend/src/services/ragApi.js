import axios from 'axios';

const RAG_API_BASE_URL = (import.meta.env.VITE_RAG_API_URL || 'https://cs-compilance-dashboard.onrender.com').replace(/\/+$/, '');

const ragApi = axios.create({
  baseURL: RAG_API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export default ragApi;
