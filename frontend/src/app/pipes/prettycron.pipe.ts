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
// See the License for the specific language governing permissions and
// limitations under the License.

import { Pipe, PipeTransform } from '@angular/core';
import cronstrue from 'cronstrue';

@Pipe({
  name: 'prettycron'
})
export class PrettycronPipe implements PipeTransform {

  transform(value: string, args?: any): any {
    if (!value || value.trim() === '') {
      return '';
    }

    // Check for exactly five parts in the cron expression
    const parts = value.split(/\s+/);
    if (parts.length !== 5) {
      console.log('Invalid cron: must have exactly 5 parts');
      return 'Invalid cron expression: must have 5 parts';
    }

    try {
      return cronstrue.toString(value);
    } catch (err) {
      console.log('Cannot parse cron:', err);
      return 'Invalid cron expression';
    }
  }

}
