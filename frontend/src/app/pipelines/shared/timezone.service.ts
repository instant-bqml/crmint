// Copyright 2024 Google Inc
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific langu

import { Injectable } from '@angular/core';

@Injectable({
  providedIn: 'root'
})
export class TimezoneService {

  getShortTimeZone(): string {
    const fullTimeZone = new Intl.DateTimeFormat().resolvedOptions().timeZone;
    const date = new Date();
    return date.toLocaleTimeString(
      'en-US', { timeZone: fullTimeZone, timeZoneName: 'short' }
    ).split(' ').pop() || fullTimeZone;
  }

  formatToLocalTimezone(utcTime: string | null): string {
    if (!utcTime) {
      return '';
    }
    try {
      const date = new Date(utcTime);
      if (isNaN(date.getTime())) {
        throw new Error('Invalid time value');
      }
      const options: Intl.DateTimeFormatOptions = {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: false,
        timeZone: Intl.DateTimeFormat().resolvedOptions().timeZone
      };
      const formattedDate = new Intl.DateTimeFormat('en-US', options).format(date);
      const [month, day, year] = formattedDate.split(', ')[0].split('/');
      const time = formattedDate.split(', ')[1];
      return `${year}-${month}-${day} ${time}`;
    } catch (error) {
      console.error('Error formatting date:', error);
      return 'Invalid Date';
    }
  }
}
