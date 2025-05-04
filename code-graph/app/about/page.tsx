'use client'

import { BookOpen, Github, HomeIcon } from 'lucide-react';
import Link from 'next/link';
import Image from 'next/image';

export default function AboutPage() {
  return (
    <main className="h-screen flex flex-col">
      <header className="flex flex-col text-xl">
        <div className="flex items-center justify-between py-4 px-8">
          <div className="flex gap-4 items-center">
            <Link href="https://www.falkordb.com" target='_blank'>
              <Image src="/logo_02.svg" alt="FalkorDB" width={27.73} height={23.95} />
            </Link>
            <h1 className='font-bold text-[22px]'>
              О ПРОЕКТЕ
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
      
      <div className="flex-1 p-8">
        <h2 className="text-2xl font-bold mb-4">О Code Graph</h2>
        <p className="mb-4">
          Code Graph - это инструмент для визуализации и анализа структуры кода в виде графа.
          Он помогает разработчикам лучше понимать связи между различными компонентами кода.
        </p>
        <h3 className="text-xl font-bold mb-2">Основные возможности:</h3>
        <ul className="list-disc pl-6 mb-4">
          <li>Визуализация зависимостей кода</li>
          <li>Поиск путей между компонентами</li>
          <li>Анализ структуры проекта</li>
          <li>Интерактивное исследование кода</li>
        </ul>
      </div>
    </main>
  )
} 