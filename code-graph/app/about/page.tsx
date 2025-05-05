'use client'

import { BookOpen, Github, HomeIcon } from 'lucide-react';
import Link from 'next/link';
import Image from 'next/image';
import React, { useEffect, useState } from 'react';
import ReactMarkdown from 'react-markdown';

export default function WikiPage() {
  const [content, setContent] = useState('Загрузка...');

  useEffect(() => {
    fetch('/wiki/intro.md')
      .then(res => res.text())
      .then(setContent)
      .catch(() => setContent('Файл не найден.'));
  }, []);

  return (
    <main className="h-screen flex flex-col">
      <header className="flex flex-col text-xl">
        <div className="flex items-center justify-between py-4 px-8">
          <div className="flex gap-4 items-center">
            <Link href="https://www.falkordb.com" target='_blank'>
              <Image src="/logo_02.svg" alt="FalkorDB" width={27.73} height={23.95} />
            </Link>
            <h1 className='font-bold text-[22px]'>
              ВИКИ
            </h1>
          </div>
          <ul className="flex gap-4 items-center font-medium">
            <Link title="Home" className="flex gap-2.5 items-center p-4" href="/">
              <HomeIcon />
              <p>Главная</p>
            </Link>
            <Link title="Github" className="flex gap-2.5 items-center p-4" href="https://github.com/FalkorDB/code-graph" target='_blank'>
              <Github />
              <p>Github</p>
            </Link>
          </ul>
        </div>
        <div className='h-2.5 bg-gradient-to-r from-[#EC806C] via-[#B66EBD] to-[#7568F2]' />
      </header>
      <div className="flex-1 p-8 prose max-w-3xl mx-auto">
        <ReactMarkdown>{content}</ReactMarkdown>
      </div>
    </main>
  )
} 