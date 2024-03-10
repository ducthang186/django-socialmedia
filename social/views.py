from django.views.generic import CreateView, UpdateView, View, DeleteView
from django.urls import reverse_lazy
from profiles.models import Profile
from .models import Friendship, Follow, Group, GroupPost, GroupMembership,  MessageGroup, Block, GroupComment, GroupReply
from .forms import FriendshipForm, FollowForm, GroupForm, GroupPostForm, GroupCommentForm, GroupReplyForm
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404, redirect, render
from django.http import Http404, HttpResponseRedirect, JsonResponse, HttpResponseNotFound
from django.db.models import Q
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator


User = get_user_model()
# views.py

@login_required(login_url='/auth/login/')
def Group_Posts(request, group_id):
    # Lấy thông tin nhóm dựa trên group_id
    group = Group.objects.get(id=group_id)
    friends = User.objects.filter(
                Q(friendships1__user2=request.user, friendships1__status='friends') |
                Q(friendships2__user1=request.user, friendships2__status='friends')
            ).exclude(
            # Loại bỏ người dùng đã chặn người dùng hiện tại
            id__in=Block.objects.filter(blocker=request.user).values('blocked_user')
        ).exclude(
            # Loại bỏ người dùng đã bị người dùng hiện tại chặn
            id__in=Block.objects.filter(blocked_user=request.user).values('blocker')
        ).exclude(
            # Loại bỏ người dùng hiện tại
            pk=request.user.id
        ).distinct()
    
    # Lấy tất cả bài viết thuộc nhóm đó
    following = Follow.objects.filter(followee=request.user).values_list('follower', flat=True)
    posts = GroupPost.objects.filter(Q(group=group) & Q(author = request.user) |Q(author__in=following) | Q(author__in=friends)).exclude(
        author__in=Block.objects.filter(blocker=request.user).values_list('blocked_user__id', flat=True)
        ).exclude( Q(group_comments__user__in=Block.objects.filter(blocker=request.user).values_list('blocked_user__id', flat=True)) |
    Q(group_comments__group_replies__user__in=Block.objects.filter(blocker=request.user).values_list('blocked_user__id', flat=True))).order_by('-created_at')

    # danh sách người dùng tham gia nhóm
    members = User.objects.filter(groupmembership__group=group).exclude(
            # Loại bỏ người dùng đã bị người dùng hiện tại chặn
            id__in=Block.objects.filter(blocked_user=request.user).values('blocker')
        ).exclude(
            # Loại bỏ người dùng đã chặn người dùng hiện tại
            id__in=Block.objects.filter(blocker=request.user).values('blocked_user')
        ).distinct()
    # danh sách nhóm gợi ý
    user_groups = GroupMembership.objects.filter(user=request.user, status='approved')
    # danh sách nhóm đã tham gia    
    groups_joined = GroupMembership.objects.filter(user=request.user, status='approved').values_list('group', flat=True)
    # danh sách nhóm bị từ chối
    groups_rejected = GroupMembership.objects.filter(user=request.user, status='rejected').values('group')
    # danh sách gợi ý
    if not groups_joined:
        groups_not_joined = Group.objects.all()
    else:
        groups_not_joined = Group.objects.all().exclude(
        Q(id__in=groups_joined) | Q (id__in = groups_rejected)
        )
    # kiểm tra là thành viên của nhóm
    is_member = GroupMembership.objects.filter(user=request.user, group=group,status='approved').exists()
    # trạng thái
    status = GroupMembership.objects.get(user=request.user, group=group).status if is_member else None

    # hiển thị thông báo
    groups = Group.objects.filter(creator=request.user)
    memberships = GroupMembership.objects.filter(
        group__in=groups,
        status='requested'
    )
    # Lấy các group_ids mà có thông báo
    group_ids_with_messages = memberships.values_list('group', flat=True)
    messages = MessageGroup.objects.all()

    # edit group post
    group_post_list = GroupPost.objects.all().order_by('-created_at')
    post_forms = []
    for post in group_post_list:
        current_post = GroupPost.objects.get(id=post.id)
        form = GroupPostForm(instance=current_post)
        
        # Thêm biểu mẫu của bài viết hiện tại vào danh sách
        post_forms.append({'post': current_post, 'form': form})

    # current_group = get_object_or_404(GroupPost, id=group_id)
    group_form = GroupForm(instance=group)


    profiles = Profile.objects.all()

    #danh sách bạn bè
    suggest_friends = User.objects.exclude(
            # Loại bỏ người dùng là bạn của người dùng hiện tại
            Q(friendships1__user2=request.user, friendships1__status='friends') |
            Q(friendships2__user1=request.user, friendships2__status='friends')
        ).exclude(
            # Loại bỏ người dùng đã chặn người dùng hiện tại
            id__in=Block.objects.filter(blocker=request.user).values('blocked_user')
        ).exclude(
            # Loại bỏ người dùng đã bị người dùng hiện tại chặn
            id__in=Block.objects.filter(blocked_user=request.user).values('blocker')
        ).exclude(
            # Loại bỏ người dùng hiện tại
            pk=request.user.id
        )
    
    invite_friends = Friendship.objects.filter(
        Q(user2=request.user, status='pending')
    ).order_by('-created_at')

    

    context = {
        'group': group,
        'posts': posts,
        'groups_joined':user_groups,
        'groups_not_joined':groups_not_joined,
        'is_member':is_member,
        'members':members,
        'status':status,
        'messages':messages,
        'post_forms':post_forms,
        'group_form':group_form,
        'profiles':profiles,
        'friends':friends,
        'invite_friends':invite_friends,
        'suggest_friends':suggest_friends,
    }
    
    return render(request, 'group_posts.html', context)



@method_decorator(login_required(login_url='/auth/login/'), name='dispatch')
class SendFriendRequestView(CreateView):
    model = Friendship
    form_class = FriendshipForm

    def dispatch(self, request, *args, **kwargs):
        user_block_list = Block.objects.filter(blocker = self.request.user)
        user2 = get_object_or_404(User, pk=kwargs['user_id'])
        user1 = request.user
        is_user2_blocked = Block.objects.filter(Q(blocked_user=user2, blocker = user1)|Q(blocked_user=user1, blocker = user2)).exists()
        if not is_user2_blocked:
            friendship, created = Friendship.objects.get_or_create(
                user1=user1,
                user2=user2,
                defaults={'status': 'pending'}
            )
            Follow.objects.create(
                followee = user1,
                follower= user2
            )
            if created:
                # Yêu cầu kết bạn được tạo mới
                pass  # Bạn có thể thêm mã xử lý tại đây nếu cần
            else:
                # Yêu cầu kết bạn đã tồn tại
                pass  # Bạn có thể thêm mã xử lý tại đây nếu cần

        else:
            Friendship.objects.filter(Q(user1=request.user, user2=user2) | Q(user1=user2, user2=request.user)).delete()

            # Xóa mối quan hệ theo dõi nếu có
            Follow.objects.filter(follower=user2, followee=request.user).delete()
            return render(request, 'error.html')

        return redirect(reverse_lazy('profiles:profile', kwargs={'pk': user2.id}))
    

    def get_success_url(self):
        # Phương thức này không còn cần thiết nữa, vì chúng ta đã xử lý mọi thứ trong dispatch
        pass


@method_decorator(login_required(login_url='/auth/login/'), name='dispatch')
class AcceptFriendRequestView(UpdateView):
    model = Friendship
    form_class = FriendshipForm
    def post(self, request, *args, **kwargs):
        friendship = get_object_or_404(Friendship, pk=kwargs['pk'])
        if friendship.user2 == request.user and friendship.status == 'pending':
            friendship.status = 'friends'
            friendship.save()
            new_friendship = Friendship.objects.create(
                user1=friendship.user2,
                user2=friendship.user1,
                status='friends'
            )
        elif friendship.user1 == request.user:
            return render(request, 'error.html')
        else:
            return render(request, 'error.html')
        return redirect('home')   
    def get_success_url(self):
        # Phương thức này không còn cần thiết nữa, vì chúng ta đã xử lý mọi thứ trong post
        pass

class RejectFriendRequestView(CreateView):
    def post(self, request, pk):
        friend_request = get_object_or_404(Friendship, id=pk)
        friend_request.delete()

        return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))
    

class CancelFriendRequestView(View):
    def post(self, request, pk):
        # Tìm kiếm yêu cầu kết bạn dựa trên id
        friend_request = get_object_or_404(Friendship, id=pk)
        follow = get_object_or_404(Follow,followee = friend_request.user1,
            follower= friend_request.user2)
        # Kiểm tra xem người dùng hiện tại có liên quan đến yêu cầu kết bạn không
        if request.user == friend_request.user1 or request.user == friend_request.user2:
            # Xóa yêu cầu kết bạn
            friend_request.delete()
            follow.delete()
            # Nếu yêu cầu kết bạn đã được chấp nhận, thì xóa cả đối tượng Friendship mới
            if friend_request.status == 'friends':
                Friendship.objects.filter(user1=friend_request.user2, user2=friend_request.user1).delete()

        # Chuyển hướng đến trang profile hoặc nơi khác phù hợp
        return redirect('profiles:profile', pk=friend_request.user2.id)

class FollowUserView(View):
    def dispatch(self, request, *args, **kwargs):
        _follower = get_object_or_404(User, pk=kwargs['user_id'])
        follower, created = Follow.objects.get_or_create(follower=_follower, followee=request.user)
        return redirect(reverse_lazy('profiles:profile', kwargs={'pk': _follower.pk}))

class UnfollowUserView(View):
    def dispatch(self, request, *args, **kwargs):
        try:
            _follower = get_object_or_404(User, pk=kwargs['user_id'])
            follower = Follow.objects.get(follower=_follower, followee=request.user)
            follower.delete()
        except Follow.DoesNotExist:
            return render(request, 'error.html')

        return redirect(reverse_lazy('profiles:profile', kwargs={'pk': _follower.pk}))



# Group 

@method_decorator(login_required(login_url='/auth/login/'), name='dispatch')
class CreateGroup(CreateView):
    template_name = 'groups.html'

    def get(self, request):
        form = GroupForm()  # Tạo một mẫu trống để hiển thị
        return render(request, self.template_name, {'form': form})

    def post(self, request):
        form = GroupForm(request.POST, request.FILES)  # Truyền dữ liệu từ POST và FILES vào mẫu
        if form.is_valid():
            group = form.save(commit=False)  # Lưu nhóm vào cơ sở dữ liệu
            group.creator = self.request.user
            group.save()
            GroupMembership.objects.create(user=self.request.user, group=group)
            return redirect('social:group_posts', group_id=group.id)  # Chuyển hướng đến trang bài viết của nhóm vừa tạo

        return render(request, self.template_name, {'form': form})
    

@method_decorator(login_required(login_url='/auth/login/'), name='dispatch')
class DeleteGroup(View):
    def post(self, request, group_id):
        group = get_object_or_404(Group, id=group_id)
        if request.user.id == group.creator.id:
            group.delete()
        return redirect('group')  # Điều hướng sau khi xóa

    def get(self, request, group_id):
        group = get_object_or_404(Group, id=group_id)
        if request.user.id == group.creator.id:
            group.delete()
        return redirect('group')

@method_decorator(login_required(login_url='/auth/login/'), name='dispatch')
class EditGroup(View):
     def post(self, request, group_id):
        group = get_object_or_404(Group, id=group_id)
        form = GroupForm(request.POST, request.FILES, instance=group)

        if form.is_valid():
            form.save()
            return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))
        return redirect('group',{'form': form, 'group': group})
     

@method_decorator(login_required(login_url='/auth/login/'), name='dispatch')
class CreateGroupPostView(CreateView):
    model = GroupPost
    form_class = GroupPostForm
    template_name = 'create_group_post.html'

    def form_valid(self, form):
        group_id = self.kwargs.get('group_id')
        group = get_object_or_404(Group, id=group_id)
        if  group.members.filter(id=self.request.user.id).exists():
            post = form.save(commit=False)
            post.group = group
            post.author = self.request.user
            post.save()

            message = MessageGroup.objects.create(
                group=group,
                user=self.request.user,
                message=f"Đã thêm bài viết mới: {post.title}",
                post=post
            )
        else:
            return HttpResponseNotFound("không thể thêm bài viết")
        return super().form_valid(form)
    
    def get_success_url(self):
        group_id = self.kwargs.get('group_id')
        return reverse_lazy('social:group_posts', args=[group_id])

@method_decorator(login_required(login_url='/auth/login/'), name='dispatch')
class DeleteGroupPost(View):
    def post(self, request, post_id):
        post = get_object_or_404(GroupPost, id=post_id)
        if request.user == post.user or request.user == post.group.creator:
            post.delete()
            message = MessageGroup.objects.create(
            group=post.group,
            user=self.request.user,
            message=f"Đã xóa bài viết: {post.title}",
            post=post
        )
        return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))
            
    def get(self, request, post_id):
        post = get_object_or_404(GroupPost, id=post_id)
        if request.user == post.author or request.user == post.group.creator:
            post.delete()

        return redirect('group')

# edit post
@method_decorator(login_required(login_url='/auth/login/'), name='dispatch')
class EditGroupPostView(View):

    def post(self, request, post_id):
        post = get_object_or_404(GroupPost, id=post_id)
        form = GroupPostForm(request.POST, request.FILES, instance=post)

        if form.is_valid():
            form.save()
            return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))
        return redirect('group',{'form': form, 'post': post})

@method_decorator(login_required(login_url='/auth/login/'), name='dispatch')
class ManageGroupMembershipView(CreateView):
    def post(self, request, group_id, user_id, action):
        group = get_object_or_404(Group, id=group_id)
        user = get_object_or_404(User, id=user_id)
        if request.user == group.creator:
            membership = GroupMembership.objects.get(user=user, group=group)
            if action == 'approve':
                membership.status = 'approved'
            elif action == 'reject':
                membership.status = 'rejected'
            membership.save()
        return redirect('social:group_posts', group_id=group.id)

@method_decorator(login_required(login_url='/auth/login/'), name='dispatch')
class JoinGroupView(CreateView):
    def get(self, request, group_id):
        group = get_object_or_404(Group, id=group_id)
        membership, created = GroupMembership.objects.get_or_create(user=request.user, group=group)
        message = f"{request.user.username} đã yêu cầu tham gia nhóm {group.name}"
        if not MessageGroup.objects.filter(user=request.user, group=group, message=message).exists():
            MessageGroup.objects.create(user=request.user, group=group, message=message)
        if created:
            membership.status = 'requested'
            membership.save()
        
        # Kiểm tra xem người dùng hiện tại có phải là người tạo nhóm hay không
        if request.user == group.creator:
            return redirect('social:group_posts', group_id=group.id)
        else:
            # Lựa chọn một URL bạn muốn chuyển hướng người dùng trong trường hợp người tạo nhóm không thấy thông báo.
            # Ví dụ: return redirect('social:group_posts', group_id=group.id)
            return redirect('social:group_posts', group_id=group_id) 

@method_decorator(login_required(login_url='/auth/login/'), name='dispatch')
class LeaveGroupView(CreateView):
    def post(self, request,user_id, group_id):
        group = get_object_or_404(Group, id=group_id)
        user = get_object_or_404(User,id=user_id)
        if request.user == group.creator:
            membership = GroupMembership.objects.get(user=user, group_id=group_id)
            membership.delete()  # Xóa mối quan hệ của người dùng với nhóm
            
            return redirect('social:group_posts', group_id=group_id) 

        if request.user == user:
            membership = GroupMembership.objects.get(user=user, group_id=group_id)
            membership.delete()  # Xóa mối quan hệ của người dùng với nhóm
            return redirect('group') 
        
    def get(self, request,user_id, group_id):
        group = get_object_or_404(Group, id=group_id)
        user = get_object_or_404(User,id=user_id)
        if request.user == group.creator:
            membership = GroupMembership.objects.get(user=user, group_id=group_id)
            membership.delete()  # Xóa mối quan hệ của người dùng với nhóm
            
            return redirect('social:group_posts', group_id=group_id) 

        if request.user == user:
            membership = GroupMembership.objects.get(user=user, group_id=group_id)
            membership.delete()  # Xóa mối quan hệ của người dùng với nhóm
            return redirect('group') 

# like
@login_required(login_url='/auth/login/')
def Like_Post(request, post_id):
    post = get_object_or_404(GroupPost, pk=post_id)
    liked = False
    
    # Kiểm tra xem người dùng hiện tại đã thích bài viết chưa.
    if request.user.is_authenticated:
        if request.user in post.likes.all():
            post.likes.remove(request.user)  # Nếu đã thích, loại bỏ thích.
        else:
            post.likes.add(request.user)  # Nếu chưa thích, thêm thích.
            liked = True
    
    response_data = {
        'liked': liked,
        'total_likes': post.likes.count()
    }
    
    return JsonResponse(response_data)

# comment group
# Comment
@method_decorator(login_required(login_url='/auth/login/'), name='dispatch')
class AddCommentView(View):
    def post(self, request, post_id):
        post = GroupPost.objects.get(pk=post_id)
        form = GroupCommentForm(request.POST, request.FILES) 
        if form.is_valid():
            comment = form.save(commit=False)
            comment.post = post
            comment.user = request.user
            comment.save()  

            # Trả về phản hồi JSON với thông tin comment mới (nếu cần)
        #     response_data = {
        #         'comment_id': comment.id,
        #         'content': comment.content,
        #         'user': comment.user.username,
        #         'created_at': comment.created_at.strftime('%Y-%m-%d %H:%M:%S'),
        #     }
        #     return JsonResponse(response_data)

        # return JsonResponse({'error': 'Invalid form data'})
            return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))
        return redirect('group')
    
# delete comment
@method_decorator(login_required(login_url='/auth/login/'), name='dispatch')
class DeleteCommentView(View):
    def post(self, request, comment_id):
        comment = GroupComment.objects.get(pk=comment_id)

        if request.user == comment.user:
            comment.delete()

            response_data = {'message': 'Comment deleted successfully'}
        return JsonResponse(response_data)
        
    def get(self, request, comment_id):
        return JsonResponse({'error': 'Only POST method is allowed'})
    

# edit comment
@method_decorator(login_required(login_url='/auth/login/'), name='dispatch')
class EditCommentView(View):
    def post(self, request, comment_id):
        comment = get_object_or_404(GroupComment, pk=comment_id)

        if request.user == comment.user:
            form = GroupCommentForm(request.POST, request.FILES, instance=comment)

            if form.is_valid():
                form.save()
 
            return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))
        else:
            return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))
        

# Reply
@method_decorator(login_required(login_url='/auth/login/'), name='dispatch')
class DeleteReplyView(View):
    def post(self, request, reply_id):
        reply = GroupReply.objects.get(pk=reply_id)

        if request.user == reply.user:
            reply.delete()
            response_data = {'message': 'Comment deleted successfully'}
        return JsonResponse(response_data)
    
    def get(self, request, reply_id):
        reply = GroupReply.objects.get(pk=reply_id)

        if request.user == reply.user:
            reply.delete()
            response_data = {'message': 'Comment deleted successfully'}
        return JsonResponse(response_data)


@method_decorator(login_required(login_url='/auth/login/'), name='dispatch')
class EditReplyView(View):
    def post(self, request, reply_id):
        reply = get_object_or_404(GroupReply, pk=reply_id)

        if request.user == reply.user:
            form = GroupReplyForm(request.POST, instance=reply)

            if form.is_valid():
                form.save()
            return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))
        else:
            return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))
    

@method_decorator(login_required(login_url='/auth/login/'), name='dispatch')
class AddReplyView(View):
    def post(self, request, comment_id):
        comment = get_object_or_404(GroupComment, pk=comment_id)
        reply_form = GroupReplyForm(request.POST)

        if reply_form.is_valid():
            content = reply_form.cleaned_data['content']
            user = request.user  # Lấy người dùng hiện tại
            reply = GroupReply(content=content, comment=comment, user=user)
            reply.save()
            return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))
        return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))




# block user
@login_required
def block_user(request, user_id):
    blocked_user = User.objects.get(pk=user_id)

    Friendship.objects.filter(Q(user1=request.user, user2=blocked_user) | Q(user1=blocked_user, user2=request.user)).delete()

    # Xóa mối quan hệ theo dõi nếu có
    Follow.objects.filter(follower=blocked_user, followee=request.user).delete()

    # Kiểm tra xem đã có trong danh sách chặn chưa
    if not Block.objects.filter(blocker=request.user, blocked_user=blocked_user).exists():
        Block.objects.create(blocker=request.user, blocked_user=blocked_user)
   
    return redirect('profiles:profile', pk=user_id)

@login_required
def unblock_user(request, user_id):
    blocked_user = User.objects.get(pk=user_id)
    Friendship.objects.filter(Q(user1=request.user, user2=blocked_user) | Q(user1=blocked_user, user2=request.user)).delete()

    # Xóa mối quan hệ theo dõi nếu có+
    Follow.objects.filter(follower=blocked_user, followee=request.user).delete()

    # Kiểm tra xem đã chặn chưa
    try:
        block_entry = Block.objects.get(blocker=request.user, blocked_user=blocked_user)
        block_entry.delete()  # Xóa bản ghi chặn nếu tồn tại
    except Block.DoesNotExist:
        pass  # Nếu không tìm thấy bản ghi chặn, không cần làm gì cả


    return redirect('profiles:profile', pk=user_id)