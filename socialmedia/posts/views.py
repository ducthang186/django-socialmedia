from .models import Post, Comment, Reply, Share
from .forms import PostForm, CommentForm, ReplyForm
from authentication.models import User
from profiles.models import Profile
from social.models import Group, GroupPost, GroupMembership, MessageGroup, Friendship, Block, Follow
from social.forms import GroupPostForm
from chat.models import ChatMessage
from django.http import HttpResponseRedirect, JsonResponse, HttpResponse
from django.db.models import Q
from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import View
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator

# Create your views here.
# trang chủ
# @login_required(login_url='/auth/login/')
def home1(request):
    # hiển thị thông báo
    if request.user.is_authenticated:
        groups = Group.objects.filter(creator=request.user)
        memberships = GroupMembership.objects.filter(
            group__in=groups,
            status='requested'
        )
        # Lấy các group_ids mà có thông báo
        group_ids_with_messages = memberships.values_list('group', flat=True)
        messages = MessageGroup.objects.all()

        # danh sach bài viết 
        # Lấy danh sách những người dùng đã bị chặn bởi người dùng hiện tại
        blocked_users = Block.objects.filter(blocked_user=request.user).values_list('blocker', flat=True)

        # danh sach nguoi dang theo doi
        following = Follow.objects.filter(followee=request.user).values_list('follower', flat=True)

        #danh sách bạn bè
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
        

        # Lấy những bài post mà người tạo không bị chặn
        post_list = Post.objects.filter( Q(user = request.user) |Q(user__in=following) | Q(user__in=friends)
        ).exclude(
            # Loại bỏ người dùng đã bị người dùng hiện tại chặn
            user__in=Block.objects.filter(blocked_user=request.user).values('blocker')
        ).exclude(
        user__in=Block.objects.filter(blocker=request.user).values_list('blocked_user__id', flat=True)
        ).exclude( Q(comments__user__in=Block.objects.filter(blocker=request.user).values_list('blocked_user__id', flat=True)) |
        Q(comments__replies__user__in=Block.objects.filter(blocker=request.user).values_list('blocked_user__id', flat=True))|
        Q(comments__user__in=Block.objects.filter(blocked_user=request.user).values_list('blocker__id', flat=True)) |
        Q(comments__replies__user__in=Block.objects.filter(blocked_user=request.user).values_list('blocker__id', flat=True))
        ).order_by('-created_at')


        # danh sách nhóm
        user_groups = GroupMembership.objects.filter(user=request.user, status='approved')
        # danh sách nhóm đã tham gia    
        groups_joined = GroupMembership.objects.filter(user=request.user, status='approved').values_list('group', flat=True)
        # danh sách nhóm bị từ chối
        groups_rejected = GroupMembership.objects.filter(user=request.user, status='rejected').values('group')
        # danh sách nhom chưa tham gia
        if not groups_joined:
            groups_not_joined = Group.objects.all()
        else:
            groups_not_joined = Group.objects.all().exclude(
            Q(id__in=groups_joined) | Q (id__in = groups_rejected))

        invite_friends = Friendship.objects.filter(
            Q(user2=request.user, status='pending')
        ).order_by('-created_at')
        post_forms = []

        # sửa bài viết
        form_post_list = Post.objects.all().order_by('-created_at')
        for post in form_post_list:
            current_post = Post.objects.get(id=post.id)
            form = PostForm(instance=current_post)
            
            # Thêm biểu mẫu của bài viết hiện tại vào danh sách
            post_forms.append({'post': current_post, 'form': form})
    
        profiles = Profile.objects.all()

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

        list_user = User.objects.all()

        message_list =[]
        for user_chat in list_user:
            message = ChatMessage.objects.filter(
                Q(sender=request.user, receiver__username=user_chat) | Q(sender__username=user_chat, receiver=request.user)
            ).order_by("-id").distinct()[:10]
            if message :
                message_list += message

        context = {
            'messages': messages,
            'post_list':post_list,
            'user_groups':user_groups,
            'groups_not_joined':groups_not_joined,
            'invite_friends': invite_friends,
            'form':form,
            'post_forms':post_forms,
            'friends':friends,        
            'profiles':profiles,        
            'suggest_friends':suggest_friends,        
            'blocked_users':blocked_users, 
            'list_user':list_user,        
            'message_list':message_list,    
    
        }
        return render(request, 'index.html', context)
    else: 
        return render(request, 'index.html')


@login_required(login_url='/auth/login/')
def friend(request):
    # hiển thị thông báo
    groups = Group.objects.filter(creator=request.user)
 

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
    post_list = Post.objects.all().order_by('-created_at') 
    num_friends = friends.count()
    # Lấy các group_ids mà có thông báo
    memberships = GroupMembership.objects.filter(
        group__in=groups,
        status='requested'
    )
    group_ids_with_messages = memberships.values_list('group', flat=True)
    messages = MessageGroup.objects.all()

    profiles = Profile.objects.all()
    

    return render(request, 'friends.html', {'post_list':post_list, 'friends':friends, 'num_friends':num_friends,'messages': messages, 'profiles':profiles,})


@login_required(login_url='/auth/login/')
def group(request):
    # hiển thị thông báo
    groups = Group.objects.filter(creator=request.user)
    memberships = GroupMembership.objects.filter(
    group__in=groups,
    status='requested'
    )
    # Lấy các group_ids mà có thông báo
    group_ids_with_messages = memberships.values_list('group', flat=True)
    messages = MessageGroup.objects.filter(group__in=group_ids_with_messages)

    # bạn bè
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
    # danh sach nguoi dang theo doi
    following = Follow.objects.filter(followee=request.user).values_list('follower', flat=True)
    # danh sach bài viết 
    post_list = Post.objects.all().order_by('-created_at') 
    # danh sách nhóm
    group_list = request.user.custom_groups.all()
    # danh sach bài viết trong nhóm

    group_post = GroupPost.objects.filter( Q(author = request.user) |Q(author__in=following) | Q(author__in=friends)).exclude(
        author__in=Block.objects.filter(blocker=request.user).values_list('blocked_user__id', flat=True)
        ).exclude( Q(group_comments__user__in=Block.objects.filter(blocker=request.user).values_list('blocked_user__id', flat=True)) |
    Q(group_comments__group_replies__user__in=Block.objects.filter(blocker=request.user).values_list('blocked_user__id', flat=True))).order_by('-created_at')

   # danh sách người dùng tham gia nhóm
    user_groups = GroupMembership.objects.filter(user=request.user, status='approved')
    # danh sách nhóm đã tham gia    
    groups_joined = GroupMembership.objects.filter(user=request.user, status='approved').values_list('group', flat=True)
    # danh sách nhóm bị từ chối
    groups_rejected = GroupMembership.objects.filter(user=request.user, status='rejected').values('group')
    # danh sách nhom chưa tham gia
    
    if not groups_joined:
        groups_not_joined = Group.objects.all()
    else:
        groups_not_joined = Group.objects.all().exclude(
        Q(id__in=groups_joined) | Q (id__in = groups_rejected)
        )


      # edit group post
    group_post_list = GroupPost.objects.all().order_by('-created_at')
    post_forms = []
    for post in group_post_list:
        current_post = GroupPost.objects.get(id=post.id)
        form = GroupPostForm(instance=current_post)
        
        # Thêm biểu mẫu của bài viết hiện tại vào danh sách
        post_forms.append({'post': current_post, 'form': form})

    invite_friends = Friendship.objects.filter(
        Q(user2=request.user, status='pending')
    ).order_by('-created_at')

    profiles = Profile.objects.all()

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


    return render(request, 'groups.html', {'messages': messages,'friends':friends, 'post_list':post_list, 'group_list':group_list, 'group_post':group_post, 'groups_not_joined':groups_not_joined ,'user_groups':user_groups, 'post_forms':post_forms, 'profiles':profiles, 'invite_friends':invite_friends, 'suggest_friends':suggest_friends})


# add post
@method_decorator(login_required(login_url='/auth/login/'), name='dispatch')
class AddPostView(View):
    
    template_name = 'index.html'

    def get(self, request):
        form = PostForm()  # Tạo một mẫu trống để hiển thị
        return render(request, self.template_name, {'form': form})

    def post(self, request):
        form = PostForm(request.POST, request.FILES)  # Truyền dữ liệu từ POST và FILES vào mẫu
        if form.is_valid():
            post = form.save(commit=False)  # Tạo một bài viết nhưng chưa lưu vào cơ sở dữ liệu
            post.user = request.user  # Gán người dùng hiện tại cho bài viết

            post.save()  # Lưu bài viết vào cơ sở dữ liệu   
            return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))
        return render(request, self.template_name, {'form': form})

# delete post
@method_decorator(login_required(login_url='/auth/login/'), name='dispatch')
class DeletePost(View):
    def post(self, request, post_id):
        post = get_object_or_404(Post, id=post_id, user=request.user)
        if request.user == post.user:
            post.delete()
        return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))
            
    def get(self, request, post_id):
        post = get_object_or_404(Post, id=post_id, user=request.user)
        if request.user == post.user:
            post.delete()

        return redirect('home')

# edit post
@method_decorator(login_required(login_url='/auth/login/'), name='dispatch')
class EditPostView(View):

    def post(self, request, post_id):
        post = get_object_or_404(Post, id=post_id)
        form = PostForm(request.POST, request.FILES, instance=post)

        if form.is_valid():
            form.save()
            return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))
        return redirect('home',{'form': form, 'post': post})




# Comment
@method_decorator(login_required(login_url='/auth/login/'), name='dispatch')
class AddCommentView(View):
    def post(self, request, post_id):
        post = Post.objects.get(pk=post_id)
        form = CommentForm(request.POST, request.FILES) 

        # Kiểm tra nếu cả ảnh và nội dung đều trống

        if form.is_valid():            
            comment = form.save(commit=False)
            comment.post = post
            comment.user = request.user
            
            comment.save()  
            return redirect('home')
        return redirect('home')
    
# delete comment
@method_decorator(login_required(login_url='/auth/login/'), name='dispatch')
class DeleteCommentView(View):
    def post(self, request, comment_id):
        comment = Comment.objects.get(pk=comment_id)

        if request.user == comment.user or request.user == comment.post.user :
            comment.delete()

            response_data = {'message': 'Comment deleted successfully'}
        return JsonResponse(response_data)
    def get(self, request, comment_id):
        comment = Comment.objects.get(pk=comment_id)

        if request.user == comment.user or request.user == comment.post.user :
            comment.delete()

            response_data = {'message': 'Comment deleted successfully'}
        return JsonResponse(response_data)

# edit comment
@method_decorator(login_required(login_url='/auth/login/'), name='dispatch')
class EditCommentView(View):
    def post(self, request, comment_id):
        comment = get_object_or_404(Comment, pk=comment_id)

        if request.user == comment.user :
            form = CommentForm(request.POST, request.FILES, instance=comment)

            if form.is_valid():
                form.save()
 
            return redirect('home')
        else:
            return redirect('home')

# Reply
@method_decorator(login_required(login_url='/auth/login/'), name='dispatch')
class DeleteReplyView(View):
    def post(self, request, reply_id):
        reply = Reply.objects.get(pk=reply_id)

        if request.user == reply.user or request.user == reply.comment.post.user:
            reply.delete()
            response_data = {'message': 'Comment deleted successfully'}
        return JsonResponse(response_data)
    
    def get(self, request, reply_id):
        reply = Reply.objects.get(pk=reply_id)

        if request.user == reply.user or request.user == reply.comment.post.user:
            reply.delete()
            response_data = {'message': 'Comment deleted successfully'}
        return JsonResponse(response_data)


@method_decorator(login_required(login_url='/auth/login/'), name='dispatch')
class EditReplyView(View):
    def post(self, request, reply_id):
        reply = get_object_or_404(Reply, pk=reply_id)

        if request.user == reply.user:
            form = ReplyForm(request.POST, instance=reply)

            if form.is_valid():
                form.save()
            return redirect('home')
        else:
            return redirect('home')
    
@method_decorator(login_required(login_url='/auth/login/'), name='dispatch')
class AddReplyView(View):
    def post(self, request, comment_id):
        comment = get_object_or_404(Comment, pk=comment_id)
        reply_form = ReplyForm(request.POST)

        if reply_form.is_valid():
            content = reply_form.cleaned_data['content']
            user = request.user  # Lấy người dùng hiện tại
            reply = Reply(content=content, comment=comment, user=user)
            reply.save()
            return redirect('home')
        return redirect('home')
    
# Like
@login_required(login_url='/auth/login/')
def Like_Post(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
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


# notyfication
@method_decorator(login_required(login_url='/auth/login/'), name='dispatch')
class ConfirmMembershipView(View):
    def get(self,request, user_id,group_id, action):
        # Lấy thông tin Membership dựa trên membership_id
        membership = GroupMembership.objects.get(user=user_id, group=group_id)
        message = MessageGroup.objects.get(user=user_id, group=group_id)
        
        if action == 'approve':
            membership.status = 'approved'
            membership.save()

            message.status = 'approved'
            message.delete()

        elif action == 'reject':
            membership.status = 'rejected'
            membership.save()

            message.status = 'rejected'
            message.delete()
        
        # Chuyển hướng về trang gốc, chẳng hạn là trang chứa danh sách yêu cầu
        return redirect('home')
    
    def post(self,request, user_id,group_id, action):
        # Lấy thông tin Membership dựa trên membership_id
        membership = GroupMembership.objects.get(user=user_id, group=group_id)
        message = MessageGroup.objects.get(user=user_id, group=group_id)
        
        if action == 'approve':
            membership.status = 'approved'
            membership.save()

            message.status = 'approved'
            message.save()

        elif action == 'reject':
            membership.status = 'rejected'
            membership.save()

            message.status = 'rejected'
            message.save()
        
        # Chuyển hướng về trang gốc, chẳng hạn là trang chứa danh sách yêu cầu
        return redirect('home')
    
# Share
@method_decorator(login_required(login_url='/auth/login/'), name='dispatch')
class SharePostView(View):   

    def post(self, request, post_id):
        post = get_object_or_404(Post, pk=post_id)
        user = request.user
        Share.objects.create(
        post=post,
        user=user
        )
        return redirect('profiles:profile', pk=request.user.id)

class DeleteSharePost(View):
    def get(self, request, share_id):
        share = get_object_or_404(Share, id=share_id)
        if share.user == request.user:  # Kiểm tra xem người dùng hiện tại có quyền xóa không
            share.delete()
            return redirect('profiles:profile', pk=request.user.id) # Điều hướng sau khi xóa
        else:
            # Xử lí khi người dùng không có quyền xóa
            return HttpResponse("Bạn không có quyền xóa bản ghi này.")
    def post(self, request, share_id):
        share = get_object_or_404(Share, id=share_id)
        if share.user == request.user:  # Kiểm tra xem người dùng hiện tại có quyền xóa không
            share.delete()
            return redirect('profiles:profile', pk=request.user.id) # Điều hướng sau khi xóa
        else:
            # Xử lí khi người dùng không có quyền xóa
            return HttpResponse("Bạn không có quyền xóa bản ghi này.")

def search(request):
    query = request.GET.get('q', '')
    
    # Tìm kiếm bài post theo title hoặc content

    post_results = Post.objects.filter(Q(title__icontains=query) | Q(content__icontains=query) | Q(user__username__icontains=query)).exclude(
            # Loại bỏ người dùng đã bị người dùng hiện tại chặn
            user__id__in=Block.objects.filter(blocked_user=request.user).values('blocker')
        ).distinct()
    
    # Tìm kiếm người dùng theo username
    user_results = User.objects.filter(username__icontains=query).exclude(
            # Loại bỏ người dùng đã bị người dùng hiện tại chặn
            id__in=Block.objects.filter(blocked_user=request.user).values('blocker')
        ).distinct()
    
    # Tìm kiếm nhóm theo tên nhóm
    group_results = Group.objects.filter(name__icontains=query)
    
    profiles = Profile.objects.all()
    context = {
        'query': query,
        'post_results': post_results,
        'user_results': user_results,
        'group_results': group_results,
        'profiles': profiles,
    }

    return render(request, 'search_results.html', context)

