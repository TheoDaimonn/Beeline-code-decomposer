'use client';

import Link from 'next/link';

export default function WikiPage() {
  return (
    <main className="h-screen flex flex-col">
      <header className="flex flex-col text-xl">
        <div className="flex items-center justify-between py-4 px-8">
          <div className="flex gap-4 items-center">
            <Link href="/">
              <span className="font-bold text-[22px]">Code Graph</span>
            </Link>
            <h1 className='font-bold text-[22px]'>Wiki</h1>
          </div>
          <ul className="flex gap-4 items-center font-medium">
            <Link title="Главная" className="flex gap-2.5 items-center p-4" href="/">
              <p>Главная</p>
            </Link>
            <Link title="О проекте" className="flex gap-2.5 items-center p-4" href="/about">
              <p>О проекте</p>
            </Link>
          </ul>
        </div>
        <div className='h-2.5 bg-gradient-to-r from-[#EC806C] via-[#B66EBD] to-[#7568F2]' />
      </header>
      <div className="flex-1 p-8 max-w-3xl mx-auto">
        <h2 className="text-2xl font-bold mb-4">Wiki</h2>
        <p className="mb-4">
          Добро пожаловать в раздел Wiki! Здесь вы найдете полезную информацию, инструкции и советы по использованию Code Graph.
        </p>
        <h3 className="text-xl font-bold mb-2">Содержание:</h3>
        <ul className="list-disc pl-6 mb-4">
          <li><a href="#install" className="text-blue-600 underline">Установка</a></li>
          <li><a href="#usage" className="text-blue-600 underline">Использование</a></li>
          <li><a href="#faq" className="text-blue-600 underline">FAQ</a></li>
        </ul>
        <section id="install" className="mb-8">
          <h4 className="text-lg font-semibold mb-2">Установка</h4>
          <p>1. Клонируйте репозиторий.<br/>2. Установите зависимости командой <code>npm install</code>.<br/>3. Запустите проект: <code>npm run dev</code>.</p>
        </section>
        <section id="usage" className="mb-8">
          <h4 className="text-lg font-semibold mb-2">Использование</h4>
          <p>Выберите репозиторий, исследуйте граф кода, используйте чат для анализа и поиска путей между функциями.</p>
        </section>
        <section id="faq">
          <h4 className="text-lg font-semibold mb-2">FAQ</h4>
          <p><b>Вопрос:</b> Как добавить новый проект?<br/><b>Ответ:</b> Нажмите &quot;Create new project&quot; и следуйте инструкциям.</p>
        </section>
      </div>
    </main>
  );
} 