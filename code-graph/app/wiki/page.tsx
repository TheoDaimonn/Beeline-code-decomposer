'use client';

import React, { useEffect, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import Link from 'next/link';
import Image from 'next/image';

const Page = () => {
  const [content, setContent] = useState('Загрузка...');

  useEffect(() => {
    fetch('/wiki/intro.md')
      .then(res => res.text())
      .then(setContent)
      .catch(() => setContent('Файл не найден.'));
  }, []);

  return (
    <main className="h-screen flex flex-col bg-gray-50">
      {/* Шапка */}
      <header className="flex flex-col text-xl">
        <div className="flex items-center justify-between py-4 px-8 bg-white shadow">
          <div className="flex gap-4 items-center">
            <Link href="https://www.falkordb.com" target="_blank">
              <Image src="/logo_02.svg" alt="FalkorDB" width={28} height={24} />
            </Link>
            <h1 className="font-bold text-[22px]">Вики</h1>
          </div>
          <ul className="flex gap-4 items-center font-medium">
            <Link title="Главная" className="flex gap-2.5 items-center p-4" href="/">
              <span>Главная</span>
            </Link>
            <Link title="Github" className="flex gap-2.5 items-center p-4" href="https://github.com/FalkorDB/code-graph" target="_blank">
              <span>Github</span>
            </Link>
          </ul>
        </div>
        <div className="h-2.5 bg-gradient-to-r from-[#EC806C] via-[#B66EBD] to-[#7568F2]" />
      </header>
      {/* Контент */}
      <div className="flex-1 flex justify-center items-start bg-gray-50">
        <article className="prose prose-lg max-w-3xl w-full p-8 bg-white rounded-xl shadow mt-8 custom-prose">
          <ReactMarkdown>{content}</ReactMarkdown>
        </article>
      </div>
    </main>
  );
};

export default Page; 