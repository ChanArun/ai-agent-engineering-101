import json
import unittest
from agent import execute, calculate, extract_dates, sort_numbers
from contract_net import parse_bid, choose, run, matches


class Scripted:
    def __init__(self, replies):
        self.replies = iter(replies)
        self.messages = []
    def __call__(self, messages, tools=None):
        self.messages.append(json.loads(json.dumps(messages)))
        return next(self.replies)


def response(value):
    return {'role': 'assistant', 'content': value}


def bid(participate=True, confidence=.8):
    return response(json.dumps(dict(participate=participate, confidence=confidence, reason='test')))


def call(name='calculate', arguments='{"expression":"17*23"}'):
    return {'role': 'assistant', 'content': None, 'tool_calls': [dict(id='t1', type='function', function=dict(name=name, arguments=arguments))]}


class LabTests(unittest.TestCase):
    def setUp(self):
        self.events = []
        self.emit = lambda event, **data: self.events.append(dict(event=event, **data))
        self.task = dict(id='a1', desc='Calculate 17*23.', gold='arithmetic', expected=391)

    def test_tools(self):
        self.assertEqual(calculate('(125-37)/4'), 22)
        self.assertEqual(extract_dates('on 2026-09-15 and 2026-10-02'), ['2026-09-15', '2026-10-02'])
        self.assertEqual(sort_numbers([9,-2,9,0]), [-2,0,9,9])
        for expr in ['__import__("os")', '2**999', 'True']:
            with self.assertRaises(ValueError): calculate(expr)
        with self.assertRaises(ValueError): sort_numbers([True])

    def test_bid_validation(self):
        for value in ['oops', '[]', '{"participate":"yes"}', '{"participate":true,"confidence":NaN,"reason":"x"}', '{"participate":true,"confidence":true,"reason":"x"}', '{"participate":true,"confidence":1.1,"reason":"x"}']:
            with self.assertRaises(ValueError): parse_bid(value)
        self.assertFalse(parse_bid(bid(False)['content'])['participate'])

    def test_tie_and_abstention(self):
        bids = [dict(contractor=n, participate=True, confidence=.9) for n in ['sorting', 'arithmetic']]
        self.assertEqual(choose(bids)['contractor'], 'arithmetic')
        self.assertIsNone(choose([dict(participate=False)]))

    def test_execution_observation_and_private_gold(self):
        chat = Scripted([bid(), bid(False), bid(False), call(), response('391')])
        m, e = run([self.task], 'baseline', chat, self.emit)
        self.assertEqual(m, dict(tasks=1, correct=1, messages=7, unassigned=0, misawards=0))
        self.assertEqual(e['success'], 1)
        self.assertEqual(json.loads(chat.messages[-1][-1]['content']), {'result':391})
        for messages in chat.messages:
            self.assertNotIn('gold', json.dumps(messages))
            self.assertNotIn('expected', json.dumps(messages))
        self.assertEqual(sum(x['event']=='award' for x in self.events),1)

    def test_bad_bid_and_no_bid(self):
        m,e = run([self.task], 'baseline', Scripted([response('not json'),bid(False),bid(False)]), self.emit)
        self.assertEqual(m['messages'],6)
        self.assertEqual(m['unassigned'],1)
        self.assertEqual(e['invalid_bids'],1)
        self.assertFalse(any(x['event']=='award' for x in self.events))

    def test_wrong_allocation_can_succeed(self):
        m,e = run([self.task], 'baseline', Scripted([bid(False),bid(),bid(False),response('391')]), self.emit)
        self.assertEqual(m['misawards'],1)
        self.assertEqual(e['success'],1)

    def test_wrong_answer(self):
        m,e = run([self.task], 'baseline', Scripted([bid(),bid(False),bid(False),response('390')]), self.emit)
        self.assertEqual(m['correct'],1)
        self.assertEqual(e['failed'],1)
        self.assertFalse(matches('true',1))

    def test_tool_error_recovery(self):
        chat=Scripted([call('unknown'),call(arguments='invalid'),call(),response('391')])
        result=execute(chat, 'role', self.task,self.emit)
        self.assertEqual(result['answer'],'391')
        self.assertIn('error',chat.messages[1][-1]['content'])
        self.assertIn('error',chat.messages[2][-1]['content'])

    def test_max_steps(self):
        result=execute(Scripted([call(),call()]),'role',self.task,self.emit,max_steps=2)
        self.assertEqual(result['status'],'failed')
        self.assertEqual(result['steps'],2)

    def test_conditions(self):
        prompts={}
        for condition in ['baseline','homogeneous','overconfident']:
            chat=Scripted([bid(),bid(False),bid(False),response('391')])
            run([self.task],condition,chat,self.emit)
            prompts[condition]=[m[0]['content'] for m in chat.messages]
        self.assertEqual(len(set(prompts['homogeneous'][:3])),1)
        self.assertEqual(prompts['baseline'][1:],prompts['overconfident'][1:])
        self.assertIn('Always participate',prompts['overconfident'][0])

if __name__=='__main__': unittest.main(verbosity=2)
