window.Museum = Object.freeze({
  exhibits: [
    {id:'clock',number:'01',name:'The Compliment Clock',type:'TEMPORAL APPARATUS',subtitle:'Runs exclusively on positive reinforcement.',icon:'◷',summary:'An hour passes whenever somebody says something nice.',label:'Twelve compliments make one perfectly unreasonable day.'},
    {id:'umbrella',number:'02',name:'The Reverse Umbrella',type:'METEOROLOGICAL DEVICE',subtitle:'Attracts the rain it was designed to prevent.',icon:'☂',summary:'A protective instrument with a fundamental misunderstanding of its job.',label:'Open it. See what happens.'},
    {id:'horizon',number:'03',name:'The Pocket Horizon',type:'GEOGRAPHIC INSTRUMENT',subtitle:'A complete sunset that fits in a drawer.',icon:'◒',summary:'Adjust the hour. The sky obediently follows.',label:'No actual sun is involved.'},
    {id:'apology',number:'04',name:'The Apology Engine',type:'SOCIAL MACHINERY',subtitle:'Sincere tone. Questionable accountability.',icon:'❞',summary:'An automated device for saying almost the right thing.',label:'Every apology is freshly assembled.'},
    {id:'map',number:'05',name:'The Map of Elsewhere',type:'NAVIGATIONAL OBJECT',subtitle:'Always takes you somewhere else.',icon:'⌁',summary:'A cartographic instrument that refuses to locate the present.',label:'Three turns. One impossible destination.'}
  ],
  compliments:[
    'Your hands are very punctual.','You have excellent second thoughts.','That is a magnificent minute.','Your patience deserves a holiday.',
    'You are remarkably good at existing.','What a thoughtful collection of seconds.','Your timing has lovely manners.','You make uncertainty look elegant.',
    'Even your pauses have purpose.','You are a fine example of a person.','The universe is lucky you stopped by.','You have given this clock a very nice day.'
  ],
  apologies:{
    starts:['I regret that','Please forgive me for','It was inconsiderate of me to','I accept responsibility for','I am deeply sorry that'],
    offenses:['rearranging the moon without asking','borrowing Tuesday indefinitely','teaching the stairs to wander','misplacing your favorite horizon','convincing the teapot it was a lighthouse','arriving yesterday without warning'],
    repairs:['I will return all missing minutes.','I have written a stern letter to gravity.','I offer one perfectly ordinary pebble.','I will personally apologize to the weather.','I have placed the furniture back in chronological order.','I promise to consult the map next time.']
  },
  routes:[
    ['The Station of Unsent Letters','The Orchard of Spare Keys','The Bridge of Maybe'],
    ['a staircase made of rain','a tunnel lined with forgotten names','a ferry that only travels sideways'],
    ['The Town of Nearly','The Last Tuesday','The Shore of Small Miracles']
  ]
});