def dqn_arguments(parser):
    """
    Add your arguments here if needed. The TAs will run test.py to load
    your default arguments.

    For example:
        parser.add_argument('--batch_size', type=int, default=32, help='batch size for training')
        parser.add_argument('--learning_rate', type=float, default=0.01, help='learning rate for training')
    """
    parser.add_argument('--env_name', default="CartPole-v0", help='environment name')

    parser.add_argument("--seed", default=11037, type=int)
    parser.add_argument("--hidden_size", default=16, type=int)
    parser.add_argument("--lr", default=0.02, type=float)
    parser.add_argument('--minimal_size', type=float, default=500, metavar='S', help='the minimal size of the learning')
    parser.add_argument("--grad_norm_clip", default=10, type=float)
    parser.add_argument('--num_episodes', type=int, default=110, help='the num of train epochs')
    parser.add_argument('--target_update', type=float, default=10, metavar='S', help='the frequency of the target net')

    parser.add_argument("--test", default=False, type=bool)
    parser.add_argument("--use_cuda", default=True, type=bool)
    parser.add_argument("--n_frames", default=int(30000), type=int)

    parser.add_argument('--episode', type=int, default=1000, help='number of training episodes')
    parser.add_argument('--gamma', type=float, default=0.99, help='discount factor')
    parser.add_argument('--learning_rate', type=float, default=0.0001, help='learning rate')
    parser.add_argument('--batch_size', type=int, default=64, help='batch size')
    parser.add_argument('--buffer_size', type=int, default=10000, help='replay buffer size')
    parser.add_argument('--max_epsilon', type=float, default=1.0, help='max exploration rate')
    parser.add_argument('--min_epsilon', type=float, default=0.01, help='min exploration rate')
    parser.add_argument('--epsilon_decay', type=int, default=1000, help='epsilon decay steps')
    parser.add_argument('--solved_reward', type=int, default=195, help='reward threshold to consider solved')

    return parser

